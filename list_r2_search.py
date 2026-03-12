import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv("backend/.env")

account_id = os.getenv("R2_ACCOUNT_ID")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("R2_BUCKET_NAME", "jingdiupload")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

try:
    # List more files and look for the specific ones
    response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=100)
    if 'Contents' in response:
        print(f"Total files returned: {len(response['Contents'])}")
        found = False
        target_files = ["d78ec1bef606.jpg", "5f838a4b797f.jpg", "e8b86a7c86ce.jpg"]
        for obj in response['Contents']:
            if obj['Key'] in target_files:
                print(f"FOUND: {obj['Key']}")
                found = True
        
        if not found:
            print("Target files NOT found in the first 100 objects.")
            # Print a few more to see the range
            print("First 5 files:")
            for obj in response['Contents'][:5]: print(f"- {obj['Key']}")
            print("Last 5 files:")
            for obj in response['Contents'][-5:]: print(f"- {obj['Key']}")
    else:
        print("Bucket is empty.")
except Exception as e:
    print(f"Error: {e}")
