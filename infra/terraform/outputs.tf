output "data_lake_bucket_name" {
  description = "Name of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.bucket
}

output "data_lake_bucket_arn" {
  description = "ARN of the S3 data lake bucket"
  value       = aws_s3_bucket.data_lake.arn
}

output "data_lake_bucket_regional_domain" {
  description = "Regional domain name for the S3 bucket (useful for Athena)"
  value       = aws_s3_bucket.data_lake.bucket_regional_domain_name
}

output "lambda_role_arn" {
  description = "ARN of the IAM role assumed by the ETL Lambda"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the IAM role assumed by the ETL Lambda"
  value       = aws_iam_role.lambda_role.name
}

output "s3_bronze_prefix" {
  description = "S3 URI for the Bronze (raw) layer"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/bronze/"
}

output "s3_silver_prefix" {
  description = "S3 URI for the Silver (cleaned) layer"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/silver/"
}

output "s3_gold_prefix" {
  description = "S3 URI for the Gold (aggregated) layer"
  value       = "s3://${aws_s3_bucket.data_lake.bucket}/gold/"
}
