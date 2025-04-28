variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "instance_name" {
  description = "Name for the GCP instance"
  type        = string
  default     = "pelosi-trades-notifier"
}

variable "billing_account_id" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "repository_url" {
  description = "URL of the git repository"
  type        = string
  default     = "https://github.com/USERNAME/pelosi-trades-notifier.git"
}

variable "recipient_emails" {
  description = "List of email addresses to send notifications to"
  type        = list(string)
  default     = []
} 