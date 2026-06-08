resource "random_id" "deployment" {
  byte_length = 4
}

module "vpc" {
  source = "./modules/vpc"

  deployment_id         = random_id.deployment.hex
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  database_subnet_cidrs = var.database_subnet_cidrs
  availability_zones    = var.availability_zones
  aws_region            = var.aws_region
}