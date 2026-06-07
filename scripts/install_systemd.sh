#!/usr/bin/env bash
set -euo pipefail
sudo cp systemd/jetson-voice-daemon.service /etc/systemd/system/
sudo cp systemd/jetson-voice-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jetson-voice-daemon.service jetson-voice-dashboard.service
systemctl status --no-pager jetson-voice-daemon.service jetson-voice-dashboard.service || true
