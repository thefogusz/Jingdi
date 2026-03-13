import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def list_r2_objects():
    s3 = boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
        region_name="auto"
    )
    
    bucket_name = os.getenv('R2_BUCKET_NAME')
    print(f"Listing objects in bucket: {bucket_name}")
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"- {obj['Key']} (Size: {obj['Size']} bytes)")
        else:
            print("No objects found in bucket.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_r2_objects()
