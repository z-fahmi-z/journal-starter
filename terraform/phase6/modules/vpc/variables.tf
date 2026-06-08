variable "deployment_id" {
  description = "Cloud API deployment identifier"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones to use for subnets"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR"
  type        = list(string)
}

variable "database_subnet_cidrs" {
  description = "Database subnet CIDR"
  type        = list(string)
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}