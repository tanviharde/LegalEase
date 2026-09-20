#!/usr/bin/env bash
set -o errexit

apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-mar

pip install -r requirements.txt
