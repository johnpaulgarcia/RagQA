#!/bin/bash
# Create the S3 bucket for Revival document storage

BUCKET="revival-docs-888491521698"
REGION="us-east-1"

echo "Creating S3 bucket: $BUCKET"
aws s3 mb "s3://$BUCKET" --region "$REGION"

echo "Enabling versioning..."
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled

echo "Done! Bucket $BUCKET is ready."
