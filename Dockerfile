FROM python:3.11-slim

# set workdir
WORKDIR /app

# copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy the project
COPY . /app

# expose port
EXPOSE 8050

# default env
ENV PORT=8050
ENV HOST=0.0.0.0

# run with gunicorn (bind 0.0.0.0:8050)
CMD ["gunicorn", "-b", "0.0.0.0:8050", "dashboard.app:app.server"]
