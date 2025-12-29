FROM python:3.11-slim

# Create app directory
WORKDIR /app

# Install dependencies
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY service/app.py /app/app.py

ENV NODE_NAME="default-node"

# Expose FastAPI default port
EXPOSE 8000

# Start the service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]