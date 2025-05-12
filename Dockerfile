# This is just a basic dockerfile you can play with this docker file as you please!

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev cron && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# cron job to run scheduler.py
RUN echo "* * * * * root python /app/scheduler.py >> /var/log/cron.log 2>&1" > /etc/cron.d/scheduler-job

# cron job
RUN chmod 0644 /etc/cron.d/scheduler-job && \
    crontab /etc/cron.d/scheduler-job

# Start cron and the app
CMD ["sh", "-c", "cron && tail -f /var/log/cron.log & python main.py"]
