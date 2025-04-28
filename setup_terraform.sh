#!/bin/bash

echo "Setting up Terraform for Financial Disclosure Tracker..."

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
  echo "Terraform not found. Please install Terraform first."
  echo "Visit https://developer.hashicorp.com/terraform/install for installation instructions."
  exit 1
fi

# Check if tfvars file exists, if not create one from the sample
if [ ! -f terraform.tfvars ]; then
  if [ -f terraform.tfvars.sample ]; then
    echo "terraform.tfvars not found. Creating from sample..."
    cp terraform.tfvars.sample terraform.tfvars
    echo "Please edit terraform.tfvars with your actual configuration values."
    exit 0
  else
    echo "Error: terraform.tfvars.sample not found."
    exit 1
  fi
fi

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

# Validate the configuration
echo "Validating Terraform configuration..."
terraform validate

if [ $? -eq 0 ]; then
  echo "Terraform configuration is valid."
  echo "To see the planned changes, run: terraform plan"
  echo "To apply the changes, run: terraform apply"
else
  echo "Error: Terraform configuration is invalid."
  exit 1
fi 