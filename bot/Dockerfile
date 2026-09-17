FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    discord.py==2.4.0 \
    httpx==0.27.2 \
    asyncpg==0.29.0

COPY . .

CMD ["python", "main.py"]
