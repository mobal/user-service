resource "aws_dynamodb_table" "users" {
  name         = "${var.stage}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  attribute {
    name = "username"
    type = "S"
  }

  global_secondary_index {
    name = "EmailIndex"

    key_schema {
      attribute_name = "email"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }

  global_secondary_index {
    name = "UsernameIndex"

    key_schema {
      attribute_name = "username"
      key_type = "HASH"
    }

    projection_type = "ALL"
  }
}
