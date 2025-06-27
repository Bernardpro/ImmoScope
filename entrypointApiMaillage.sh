#!/bin/bash

# Start the FastAPI server
uvicorn api:app --reload --host 0.0.0.0 --port 81
