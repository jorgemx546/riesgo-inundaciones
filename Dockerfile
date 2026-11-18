FROM python:3.13.15-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT}"]
