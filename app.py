import os
from flask import Flask, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename
import replicate
from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from spaces_utils import SpacesUploader

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure environment
ENVIRONMENT = os.getenv('FLASK_ENV', 'development')
DOMAIN = os.getenv('DOMAIN', 'localhost:5000')
PROTOCOL = 'https' if ENVIRONMENT == 'production' else 'http'

# Configure Redis Queue
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)
queue = Queue(connection=redis_conn)

# Initialize the Spaces uploader
spaces_uploader = SpacesUploader()

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/api/generate', methods=['POST'])
def generate_videos():
    try:
        data = request.get_json()
        
        # Extract parameters from request
        images = data.get('images', [])
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', '')
        aspect_ratio = str(data.get('aspectRatio', '16:9'))
        duration = int(data.get('duration', 5))
        email = data.get('email')
        
        # Validate inputs
        if not images:
            return jsonify({'error': 'No images provided'}), 400
            
        # Convert image data to proper format
        images_data = []
        for img in images:
            if isinstance(img, dict):
                img_data = {
                    'name': str(img.get('name', '')),
                    'url': str(img.get('url', ''))
                }
                images_data.append(img_data)
            else:
                return jsonify({'error': 'Invalid image data format'}), 400
        
        # Create settings dictionary
        settings = {
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'aspect_ratio': aspect_ratio,
            'duration': duration
        }
        
        # Queue the job
        from tasks import process_bulk_videos
        job = queue.enqueue(process_bulk_videos, images_data, settings, email)
        
        return jsonify({
            'status': 'success',
            'batch_id': job.id
        })
        
    except Exception as e:
        print(f"Error in generate_videos: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
