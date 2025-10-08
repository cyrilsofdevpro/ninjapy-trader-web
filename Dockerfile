# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 (Render uses this)
EXPOSE 8000

# Start your Flask or FastAPI app using Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
