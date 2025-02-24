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

# Environment variables should be set in .env file, not hardcoded here
REPLICATE_API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')
DO_SPACES_KEY = os.environ.get('DO_SPACES_KEY')
DO_SPACES_SECRET = os.environ.get('DO_SPACES_SECRET')
DO_SPACES_BUCKET = os.environ.get('DO_SPACES_BUCKET', 'comaneci-videos')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION', 'nyc3')

# Configure Redis Queue
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)
queue = Queue(connection=redis_conn)

# Configure upload settings
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Initialize the Spaces uploader
spaces_uploader = SpacesUploader()

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('output', exist_ok=True)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
