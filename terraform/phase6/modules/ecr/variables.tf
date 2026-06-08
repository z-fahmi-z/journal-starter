variable "tags" {
  description = "Tags to apply to ECR repository"
  type        = map(string)
  default     = {}
}