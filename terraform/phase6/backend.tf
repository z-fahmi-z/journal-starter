terraform {
  backend "s3" {
    bucket       = "cloud-api-tf-state"
    key          = "cloud-api-deployment/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}