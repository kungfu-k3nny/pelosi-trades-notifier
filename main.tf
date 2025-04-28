terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Define variables
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
  default     = "disclosure-tracker"
}

# Create a VPC network
resource "google_compute_network" "vpc_network" {
  name                    = "disclosure-tracker-network"
  auto_create_subnetworks = true
}

# Create a firewall rule to allow SSH
resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["disclosure-tracker"]
}

# Create a service account with minimal permissions
resource "google_service_account" "disclosure_tracker_sa" {
  account_id   = "disclosure-tracker-sa"
  display_name = "Financial Disclosure Tracker Service Account"
}

# Create a compute instance
resource "google_compute_instance" "disclosure_tracker_instance" {
  name         = var.instance_name
  machine_type = "e2-micro" # Cheapest VM type for minimal cost (~$6-8/month)
  tags         = ["disclosure-tracker"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 10 # Minimum size in GB
      type  = "pd-standard" # Standard disk for lower cost
    }
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    access_config {
      // Ephemeral IP
    }
  }

  service_account {
    email  = google_service_account.disclosure_tracker_sa.email
    scopes = ["cloud-platform"]
  }

  # Install dependencies and set up the application
  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y python3-pip git
    pip3 install -U pip
    git clone https://github.com/USERNAME/financial-disclosure-tracker.git /opt/disclosure-tracker
    cd /opt/disclosure-tracker
    pip3 install -r requirements.txt
    # Set up config file (would need to be configured properly)
    # Add a systemd service to run the application
    cat <<EOT > /etc/systemd/system/disclosure-tracker.service
[Unit]
Description=Financial Disclosure Tracker
After=network.target

[Service]
Type=simple
User=nobody
WorkingDirectory=/opt/disclosure-tracker
ExecStart=/usr/bin/python3 /opt/disclosure-tracker/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT
    
    # Enable and start the service
    systemctl enable disclosure-tracker.service
    systemctl start disclosure-tracker.service
  EOF
}

# Set up autoscaling for handling increased load if needed
resource "google_compute_instance_template" "disclosure_tracker_template" {
  name         = "disclosure-tracker-template"
  machine_type = "e2-micro"
  tags         = ["disclosure-tracker"]

  disk {
    source_image = "debian-cloud/debian-11"
    auto_delete  = true
    boot         = true
    disk_size_gb = 10
    disk_type    = "pd-standard"
  }

  network_interface {
    network = google_compute_network.vpc_network.name
    access_config {
      // Ephemeral IP
    }
  }

  service_account {
    email  = google_service_account.disclosure_tracker_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y python3-pip git
    pip3 install -U pip
    git clone https://github.com/USERNAME/financial-disclosure-tracker.git /opt/disclosure-tracker
    cd /opt/disclosure-tracker
    pip3 install -r requirements.txt
    # Set up the application
    python3 /opt/disclosure-tracker/main.py
  EOF
}

resource "google_compute_instance_group_manager" "disclosure_tracker_group" {
  name = "disclosure-tracker-group"
  zone = var.zone
  
  base_instance_name = "disclosure-tracker"
  
  version {
    instance_template = google_compute_instance_template.disclosure_tracker_template.id
  }
  
  target_size = 1

  named_port {
    name = "http"
    port = 80
  }
}

# Create an autoscaler with strict limits to prevent unexpected costs
resource "google_compute_autoscaler" "disclosure_tracker_autoscaler" {
  name   = "disclosure-tracker-autoscaler"
  zone   = var.zone
  target = google_compute_instance_group_manager.disclosure_tracker_group.id

  autoscaling_policy {
    max_replicas    = 2 # Hard cap at 2 instances to control costs
    min_replicas    = 1
    cooldown_period = 60

    cpu_utilization {
      target = 0.75 # Scale when CPU reaches 75%
    }
  }
}

# Set up a budget alert to prevent excessive spending
resource "google_billing_budget" "budget" {
  billing_account = var.billing_account_id
  display_name    = "Financial Disclosure Tracker Budget"
  
  budget_filter {
    projects = ["projects/${var.project_id}"]
    labels = {
      service = "compute"
    }
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = "50" # $50 budget (below the $60 threshold)
    }
  }

  threshold_rules {
    threshold_percent = 0.5 # Alert at 50% of budget
  }
  
  threshold_rules {
    threshold_percent = 0.8 # Alert at 80% of budget
  }
  
  threshold_rules {
    threshold_percent = 1.0 # Alert at 100% of budget
  }

  all_updates_rule {
    monitoring_notification_channels = [
      google_monitoring_notification_channel.email.name,
    ]
    disable_default_iam_recipients = true
  }
}

variable "billing_account_id" {
  description = "GCP Billing Account ID"
  type        = string
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

# Create a notification channel for budget and scaling alerts
resource "google_monitoring_notification_channel" "email" {
  display_name = "Financial Disclosure Tracker Alert Email"
  type         = "email"
  
  labels = {
    email_address = var.alert_email
  }
}

# Set up monitoring for the instances
resource "google_monitoring_alert_policy" "instance_cpu" {
  display_name = "High CPU Usage Alert"
  combiner     = "OR"
  
  conditions {
    display_name = "CPU utilization for instance"
    
    condition_threshold {
      filter          = "resource.type = \"gce_instance\" AND resource.labels.instance_id = \"${google_compute_instance.disclosure_tracker_instance.id}\" AND metric.type = \"compute.googleapis.com/instance/cpu/utilization\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8 # Alert when CPU is above 80%
      
      trigger {
        count = 1
      }
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = [
    google_monitoring_notification_channel.email.name
  ]
} 