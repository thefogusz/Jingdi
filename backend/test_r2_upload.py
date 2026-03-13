import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add backend to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.r2_service import upload_image, get_image_url
import boto3

def test_upload():
    print("Testing R2 Upload...")
    filename = "test_verify_upload.jpg"
    content = b"fake image content"
    
    try:
        url = upload_image(filename, content)
        print(f"Upload successful! URL: {url}")
        
        # Verify with boto3 list
        s3 = boto3.client(
            's3',
            endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
            aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
            region_name="auto"
        )
        
        response = s3.list_objects_v2(Bucket=os.getenv('R2_BUCKET_NAME'))
        found = False
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'] == filename:
                    print(f"✅ Found uploaded file in R2 list: {filename}")
                    found = True
                    break
        
        if not found:
            print(f"❌ Uploaded file NOT FOUND in R2 list: {filename}")
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    test_upload()
