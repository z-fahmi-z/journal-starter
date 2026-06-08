resource "aws_ecr_repository" "this" {
  name                 = "journal-repository"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  # Amazon s3 managed encryption by default 
  encryption_configuration {
    encryption_type = "AES256"
  }

  force_delete = true

  tags = merge(var.tags, {
    Name = "ecr-journal"
  })
}