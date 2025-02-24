from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'
FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

def create_drive_folder(service, folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    file = service.files().create(body=file_metadata, fields='id').execute()
    print(f"Created folder with ID: {file.get('id')}")
    return file.get('id')

def upload_file(service, file_path, folder_id):
    """Upload a file to Google Drive and return the file ID"""
    try:
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        print(f"✅ File uploaded successfully!")
        print(f"📂 View file at: {file.get('webViewLink')}")
        return file.get('id')
    except Exception as e:
        print(f"❌ Error uploading file: {str(e)}")
        return None

def test_drive_connection():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        
        print("✅ Successfully connected to Google Drive!")
        
        # Test with a sample file from output directory
        test_file = 'output/test.txt'
        if os.path.exists(test_file):
            print(f"📁 Found test file: {test_file}")
            upload_file(service, test_file, FOLDER_ID)
        else:
            print(f"❌ Test file not found: {test_file}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    test_drive_connection()
