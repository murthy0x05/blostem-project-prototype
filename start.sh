#!/bin/bash
# Automatically activate the virtual environment and start the server
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
