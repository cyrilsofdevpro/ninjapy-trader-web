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

# Start the Dash app using Gunicorn. Use shell form so $PORT set by the
# platform is respected at runtime. Default to 8000 when PORT is not set.
ENV PORT=8000
CMD sh -c "exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2"
