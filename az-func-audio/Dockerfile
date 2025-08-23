# Dockerfile for Azure Functions (Python 3.11) with dependencies installed
# Uses the official Azure Functions Python base image which is compatible
# with the Azure Functions host on Linux.

FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice

# Copy function app files
WORKDIR /home/site/wwwroot
COPY . /home/site/wwwroot

# Upgrade pip and install build deps then install Python requirements
# Installing cryptography will compile or install a compatible wheel here.
RUN apt-get update -y \
    && apt-get install -y build-essential libssl-dev libffi-dev python3-dev cargo \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt \
    && apt-get remove -y build-essential python3-dev cargo \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Expose port (Azure Functions host listens internally)
EXPOSE 80

# Default command is provided by the base image and will run the Functions host
# No CMD needed; keep base image behavior.
