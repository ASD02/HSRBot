FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY hsrbot ./hsrbot
COPY data/schedule.json ./data/schedule.json
ENV DB_PATH=/storage/hsrbot.db DATA_DIR=data PYTHONUNBUFFERED=1
VOLUME /storage
CMD ["python", "-m", "hsrbot"]
