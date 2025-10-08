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

# Start the Dash app using Gunicorn. The Dash app lives at dashboard/app.py and
# the underlying Flask server is exposed as `app.server`.
CMD ["gunicorn", "dashboard.app:app.server", "--bind", "0.0.0.0:8000", "--workers", "2"]
