# AWS

Phase 3 reads `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `S3_BUCKET_NAME` from the environment. The application does not create IAM users.

The API needs only this bucket access. Replace the bucket name. Do not attach `AdministratorAccess`, and do not use the account root user.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/*"
    }
  ]
}
```

`s3:ListBucket` is used by the startup bucket check. Bedrock, ECR, and EKS permissions are not required yet.
