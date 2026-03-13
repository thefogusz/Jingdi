"""
Cloudflare R2 upload service (S3-compatible).
Requires env vars: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
                   R2_BUCKET_NAME, R2_PUBLIC_URL
"""
import os
import boto3
from botocore.config import Config

_r2_client = None

def _get_client():
    global _r2_client
    if _r2_client is None:
        account_id = os.getenv("R2_ACCOUNT_ID")
        if not account_id:
            raise RuntimeError("R2_ACCOUNT_ID is not set")
        _r2_client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _r2_client


def upload_image(filename: str, data: bytes, content_type: str = "image/jpeg") -> str:
    """Upload image bytes to R2 and return the public URL."""
    bucket = os.getenv("R2_BUCKET_NAME", "jingdi-uploads")
    public_url_base = (os.getenv("R2_PUBLIC_URL") or "https://pub-288db4e945a94cb78539b5d398c81430.r2.dev").rstrip("/")

    client = _get_client()
    client.put_object(
        Bucket=bucket,
        Key=filename,
        Body=data,
        ContentType=content_type,
    )
    return f"{public_url_base}/{filename}"


def get_image_url(filename: str) -> str:
    """Return the public URL for a stored image."""
    public_url_base = (os.getenv("R2_PUBLIC_URL") or "https://pub-288db4e945a94cb78539b5d398c81430.r2.dev").rstrip("/")
    return f"{public_url_base}/{filename}"
