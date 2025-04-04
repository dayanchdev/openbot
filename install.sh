#!/bin/bash

# Update packages and install dependencies
apt update -y
apt upgrade -y
apt install -y python3 python3-venv python3-pip

# Create a virtual environment in the current directory
python3 -m venv venv

# Activate the virtual environment and install required Python packages
source venv/bin/activate
pip install python-telegram-bot==13.15 python-dotenv

# Deactivate the virtual environment
deactivate

# Create the openbot service file for systemd
cat <<EOL > /etc/systemd/system/openbot.service
[Unit]
Description=Openbot
After=network.target

[Service]
User=root
WorkingDirectory=/root/openbot
ExecStart=/root/openbot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd to recognize the new service, enable, and start it
systemctl daemon-reload
systemctl enable openbot
systemctl start openbot

echo "Installation complete. Success!"
