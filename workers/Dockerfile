FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    arq==0.26.1 \
    redis==5.0.8 \
    asyncpg==0.29.0

COPY . .

CMD ["python", "main.py"]
