from __future__ import annotations

import boto3

from revival.config import get_settings

_client = None


def _get_client():
    global _client
    if _client is None:
        settings = get_settings()
        kwargs = {"region_name": settings.aws_region}
        if settings.aws_access_key_id:
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        _client = boto3.client("s3", **kwargs)
    return _client


def upload_pdf(file_bytes: bytes, s3_key: str) -> str:
    """Upload a PDF to S3. Returns the s3_key."""
    client = _get_client()
    bucket = get_settings().s3_bucket
    client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=file_bytes,
        ContentType="application/pdf",
    )
    return s3_key


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL."""
    client = _get_client()
    bucket = get_settings().s3_bucket
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def delete_object(s3_key: str) -> None:
    client = _get_client()
    bucket = get_settings().s3_bucket
    client.delete_object(Bucket=bucket, Key=s3_key)
