import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv("backend/.env")

account_id = os.getenv("R2_ACCOUNT_ID")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("R2_BUCKET_NAME", "jingdiupload")

print(f"Account ID: {account_id}")
print(f"Bucket: {bucket_name}")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

try:
    response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
    if 'Contents' in response:
        print("Files in bucket:")
        for obj in response['Contents']:
            print(f"- {obj['Key']}")
    else:
        print("Bucket is empty.")
except Exception as e:
    print(f"Error: {e}")
