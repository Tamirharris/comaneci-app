import os
import base64
import replicate
from spaces_utils import SpacesUploader
from flask_mail import Mail, Message
import json
from datetime import datetime

# Initialize the Spaces uploader
spaces_uploader = SpacesUploader()

def save_job_status(job_id, status, data=None):
    """Save job status to a JSON file"""
    status_file = os.path.join('output', 'job_status.json')
    os.makedirs('output', exist_ok=True)
    
    try:
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                statuses = json.load(f)
        else:
            statuses = {}
        
        statuses[job_id] = {
            'status': status,
            'data': data,
            'updated_at': datetime.now().isoformat()
        }
        
        with open(status_file, 'w') as f:
            json.dump(statuses, f)
    except Exception as e:
        print(f"Error saving job status: {e}")

def process_video(image_url, settings, job_id, notification_email=None):
    """
    Background task to process a video
    """
    try:
        save_job_status(job_id, 'processing', {
            'message': 'Starting video generation',
            'progress': 0
        })

        # Generate video using Replicate
        output = replicate.run(
            "kwaivgi/kling-v1.6-standard:7e324e5fcb9479696f15ab6da262390cddf5a1efa2e11374ef9d1f85fc0f82da",
            input={
                "start_image": image_url,  # Pass the URL directly
                "prompt": settings.get('prompt', ''),
                "negative_prompt": settings.get('negative_prompt', ''),
                "aspect_ratio": settings.get('aspect_ratio', '16:9'),
                "duration": int(settings.get('duration', 5)),
                "cfg_scale": float(settings.get('cfg_scale', 0.5))
            }
        )

        if output:
            video_url = str(output)
            
            save_job_status(job_id, 'processing', {
                'message': 'Uploading to Spaces...',
                'progress': 50
            })

            # Upload to Spaces
            filename = f"{settings.get('filename', 'video')}_{job_id}.mp4"
            spaces_url = spaces_uploader.upload_from_url(video_url, filename)
            
            if spaces_url:
                result = {
                    'message': 'Video generated and uploaded successfully!',
                    'video_url': spaces_url
                }
                save_job_status(job_id, 'completed', result)

                # Send email notification if email provided
                if notification_email:
                    try:
                        send_completion_email(notification_email, spaces_url, settings.get('filename', 'video'))
                    except Exception as e:
                        print(f"Failed to send email: {e}")
                
                return result
            else:
                error = "Failed to upload video to Spaces"
                save_job_status(job_id, 'failed', {'error': error})
                return {'error': error}
        else:
            error = "No output received from Replicate"
            save_job_status(job_id, 'failed', {'error': error})
            return {'error': error}
            
    except Exception as e:
        error = f"Processing error: {str(e)}"
        save_job_status(job_id, 'failed', {'error': error})
        return {'error': error}

def process_bulk_videos(images_data, settings, notification_email=None):
    """
    Process multiple videos in sequence
    """
    results = []
    total = len(images_data)
    batch_id = base64.urlsafe_b64encode(os.urandom(6)).decode('ascii')
    
    for idx, image_data in enumerate(images_data):
        job_id = f"bulk_{batch_id}_{idx}"
        
        # Update settings with image-specific data
        image_settings = settings.copy()
        
        # Ensure we have a string filename, not a dict
        filename = image_data.get('name', '')
        if isinstance(filename, dict):
            filename = str(filename.get('name', f'video_{idx}'))
        elif not filename:
            filename = f'video_{idx}'
            
        image_settings['filename'] = filename
        
        try:
            # Get the image URL, ensuring it's a string
            image_url = image_data.get('url', '')
            if isinstance(image_url, dict):
                image_url = str(image_url.get('url', ''))
            
            if not image_url:
                raise ValueError("No valid image URL provided")
                
            # Process the video
            result = process_video(
                image_url,
                image_settings,
                job_id,
                notification_email
            )
            results.append({
                'job_id': job_id,
                'filename': image_settings['filename'],
                'result': result
            })
        except Exception as e:
            print(f"Error processing video {idx}: {str(e)}")
            results.append({
                'job_id': job_id,
                'filename': image_settings['filename'],
                'error': str(e)
            })
    
    # Send batch completion email
    if notification_email:
        send_batch_completion_email(notification_email, results, batch_id)
    
    return results

def send_completion_email(email, video_url, filename):
    """Send email notification when a video is ready"""
    try:
        mail = Mail()
        msg = Message(
            'Your video is ready!',
            sender='noreply@comaneci.com',
            recipients=[email]
        )
        msg.body = f"""Your video {filename} is ready!
You can download it here: {video_url}

Thanks for using Comaneci!"""
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")

def send_batch_completion_email(email, results, batch_id):
    """Send email notification when a batch is complete"""
    try:
        mail = Mail()
        msg = Message(
            'Your batch of videos is ready!',
            sender='noreply@comaneci.com',
            recipients=[email]
        )
        
        # Create message body
        body = [f"Your batch of videos (Batch ID: {batch_id}) is ready!\n"]
        for result in results:
            if 'error' in result:
                body.append(f"❌ {result['filename']}: Failed - {result['error']}")
            else:
                body.append(f"✅ {result['filename']}: {result['result']['video_url']}")
        
        msg.body = "\n".join(body)
        mail.send(msg)
    except Exception as e:
        print(f"Error sending batch completion email: {e}")
