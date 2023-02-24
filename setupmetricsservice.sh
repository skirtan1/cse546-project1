#!/usr/bin/env bash

sudo rm /lib/systemd/system/service.service
sudo rm /lib/systemd/system/timer.timer

# Stop service
sudo systemctl stop metrics.timer
sudo systemctl stop metrics.service

# Disable service
sudo systemctl disable metrics.timer
sudo systemctl disable metrics.service

# Copy metrics service systemd files to location
sudo cp custom_metrics.service /lib/systemd/system/
sudo cp custom_metrics.timer /lib/systemd/system/

# Add required permissions
sudo chmod u+x /lib/systemd/system/metrics.service
sudo chmod u+x /lib/systemd/system/metrics.timer

# Enable service
sudo systemctl enable metrics.timer
sudo systemctl enable metrics.service

# Start metrics service
sudo systemctl start metrics.timer
sudo systemctl start metrics.service

# Test commands
sudo systemctl status metrics.service
sudo systemctl status metrics.timer
sudo journalctl -u metrics.service
sudo journalctl -u metrics.timer
sudo systemctl list-timers