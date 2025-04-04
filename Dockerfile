FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    openvpn wget curl iproute2 iptables net-tools && \
    apt-get clean

# Copy OpenVPN deb and install it
COPY openvpn_2.4.8-bionic0_amd64.deb /tmp/
RUN dpkg -i /tmp/openvpn_2.4.8-bionic0_amd64.deb || apt-get install -f -y

# Set working directory
WORKDIR /opt/openbot

# Copy project files
COPY . .

# Set up Python virtualenv and install packages
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install python-telegram-bot==13.15 python-dotenv

# Expose VPN port if needed
EXPOSE 1194/udp

# Run the bot
CMD ["/bin/bash", "-c", ". venv/bin/activate && python3 main.py"]
