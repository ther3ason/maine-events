variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short identifier used to namespace all resources"
  type        = string
  default     = "portland-events"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "s3_bucket_name" {
  description = "Globally unique name for the S3 data lake bucket"
  type        = string
  default     = "portland-events-data-lake"
}

variable "lambda_role_name" {
  description = "Name of the IAM role assumed by the Lambda ETL function"
  type        = string
  default     = "portland-events-lambda-role"
}
