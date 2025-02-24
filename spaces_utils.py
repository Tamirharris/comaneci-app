import os
import boto3
import requests
from botocore.client import Config

class SpacesUploader:
    def __init__(self):
        # Set up credentials
        self.spaces_key = 'DO8017PTXKHZHYF3GLC3'
        self.spaces_secret = '8hyq2IcxEb5nXW0a7QsS9BMyanDQbhYdMTUqkIun4SU'
        self.bucket = 'comaneci-videos'
        self.region = 'nyc3'
        
        self.session = boto3.session.Session()
        self.client = self.session.client('s3',
            region_name=self.region,
            endpoint_url=f"https://{self.region}.digitaloceanspaces.com",
            aws_access_key_id=self.spaces_key,
            aws_secret_access_key=self.spaces_secret,
            config=Config(s3={'addressing_style': 'virtual'})
        )
        print(f"🚀 Initialized Spaces uploader for bucket: {self.bucket}")

    def upload_from_url(self, url, filename=None):
        """Upload a file directly from a URL to Spaces"""
        try:
            # If no filename provided, use the last part of the URL
            if not filename:
                filename = url.split('/')[-1]
            
            # Stream the file from URL directly to Spaces
            print(f"📥 Downloading from {url} and uploading to Spaces...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Upload to videos/ folder
            key = f"videos/{filename}"
            self.client.upload_fileobj(
                response.raw,
                self.bucket,
                key,
                ExtraArgs={
                    'ACL': 'public-read',
                    'ContentType': 'video/mp4'  # This tells browsers it's a playable video
                }
            )
            
            # Generate the public URL
            spaces_url = f"https://{self.bucket}.{self.region}.digitaloceanspaces.com/{key}"
            print(f"✅ Upload complete! Video available at: {spaces_url}")
            
            return spaces_url
            
        except Exception as e:
            print(f"❌ Failed to upload from URL: {str(e)}")
            return None

    def test_connection(self):
        """Test connection to Spaces"""
        try:
            self.client.list_objects(Bucket=self.bucket)
            print("✅ Successfully connected to Spaces!")
            return True
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            return False
