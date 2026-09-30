FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser
COPY app ./app
COPY migrations ./migrations
COPY start.sh ./start.sh
RUN chmod +x ./start.sh && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["./start.sh"]
