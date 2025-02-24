from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaUploadProgress
import os
from dotenv import load_dotenv
import time
from typing import Optional, Callable

# Load environment variables
# load_dotenv()  # Removed from here

class DriveUploader:
    def __init__(self):
        load_dotenv()  # Move this here to ensure it loads
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if not self.folder_id:
            print("❌ GOOGLE_DRIVE_FOLDER_ID not found in environment variables")
            print(f"Looking in: {os.path.abspath('.env')}")
        else:
            print(f"📂 Found folder ID: {self.folder_id}")
        self.service = self._create_drive_service()
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def _create_drive_service(self):
        """Create and return an authorized Drive API service instance."""
        SCOPES = ['https://www.googleapis.com/auth/drive']  # Changed from drive.file to drive
        SERVICE_ACCOUNT_FILE = 'service_account.json'

        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            return build('drive', 'v3', credentials=credentials)
        except Exception as e:
            print(f"❌ Error creating Drive service: {str(e)}")
            return None

    def _upload_with_progress(self, media_body, file_metadata, 
                            on_progress: Optional[Callable[[float], None]] = None,
                            prediction_id: Optional[str] = None):
        """Upload a file with progress tracking and retry logic."""
        for attempt in range(self.max_retries):
            try:
                request = self.service.files().create(
                    body=file_metadata,
                    media_body=media_body,
                    fields='id, webViewLink'
                )

                response = None
                last_progress = 0
                
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        progress = status.progress()
                        if progress > last_progress:
                            last_progress = progress
                            if on_progress:
                                on_progress(progress)
                            if prediction_id:
                                self._update_prediction_status(prediction_id, progress)

                return response
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                time.sleep(self.retry_delay * (attempt + 1))
                continue

    def _update_prediction_status(self, prediction_id: str, progress: float):
        """Update the prediction status with upload progress."""
        from app import predictions  # Import here to avoid circular import
        if prediction_id in predictions:
            predictions[prediction_id].update({
                'drive_upload_progress': round(progress * 100, 2),
                'message': f'Uploading to Drive: {round(progress * 100)}%'
            })

    def upload_video(self, video_path: str, 
                    on_progress: Optional[Callable[[float], None]] = None,
                    prediction_id: Optional[str] = None) -> Optional[str]:
        """Upload a video file to Google Drive and return its web view link."""
        if not self.service:
            print("❌ Drive service not initialized")
            return None

        try:
            file_metadata = {
                'name': os.path.basename(video_path),
                'parents': [self.folder_id]
            }
            
            media = MediaFileUpload(
                video_path, 
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            response = self._upload_with_progress(
                media, 
                file_metadata, 
                on_progress,
                prediction_id
            )
            
            print(f"✅ Video uploaded successfully to Drive!")
            return response.get('webViewLink')
            
        except Exception as e:
            print(f"❌ Error uploading video: {str(e)}")
            return None

    def upload_from_url(self, url: str, filename: str,
                    on_progress: Optional[Callable[[float], None]] = None,
                    prediction_id: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive directly from a URL without saving locally."""
        if not self.service:
            print("❌ Drive service not initialized")
            return None

        try:
            import requests
            from io import BytesIO

            # Get file size
            response = requests.head(url)
            file_size = int(response.headers.get('content-length', 0))

            # Create a streaming upload
            def generate_media():
                downloaded = 0
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        downloaded += len(chunk)
                        if on_progress:
                            progress = downloaded / file_size
                            on_progress(progress)
                        yield chunk

            file_metadata = {
                'name': filename,
                'parents': [self.folder_id] if self.folder_id else None
            }

            media = MediaFileUpload(
                BytesIO(),
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024
            )

            # Override the media's stream with our generator
            media._stream = generate_media()
            media._size = file_size

            response = self._upload_with_progress(
                media,
                file_metadata,
                on_progress,
                prediction_id
            )

            if response:
                return response.get('webViewLink')
            return None

        except Exception as e:
            print(f"❌ Error uploading from URL: {str(e)}")
            return None

    def test_folder_access(self):
        """Test if we can access the configured Google Drive folder."""
        if not self.service:
            print("❌ Drive service not initialized")
            return False
        
        try:
            print("🔍 Testing Drive API access...")
            # First try to list files to verify basic access
            results = self.service.files().list(
                pageSize=10,
                fields="nextPageToken, files(id, name)"
            ).execute()
            files = results.get('files', [])
            print(f"✅ Successfully listed {len(files)} files/folders")
            
            if files:
                print("\nAccessible files/folders:")
                for file in files:
                    print(f"- {file.get('name')} (ID: {file.get('id')})")
            
            print(f"\n🔍 Testing specific folder access...")
            print(f"Folder ID: {self.folder_id}")
            
            # Try to get folder metadata
            folder = self.service.files().get(
                fileId=self.folder_id,
                fields='name, id'
            ).execute()
            
            print(f"✅ Successfully connected to Drive folder:")
            print(f"   - Folder Name: {folder.get('name')}")
            print(f"   - Folder ID: {folder.get('id')}")
            return True
        except Exception as e:
            print(f"❌ Error accessing folder: {str(e)}")
            if hasattr(e, 'error_details'):
                print(f"Error details: {e.error_details}")
            return False

if __name__ == "__main__":
    uploader = DriveUploader()
    uploader.test_folder_access()
    test_file = "output/test.mp4"
    
    def print_progress(progress: float):
        print(f"Upload progress: {round(progress * 100)}%")
        
    if os.path.exists(test_file):
        link = uploader.upload_video(test_file, on_progress=print_progress)
        if link:
            print(f"📂 View video at: {link}")
    else:
        print(f"❌ Test file not found: {test_file}")
