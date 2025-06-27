#!/bin/bash

# Update requirements
# pip freeze > requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 82