FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.6 \
    asyncpg==0.29.0 \
    redis==5.0.8 \
    motor==3.5.1 \
    pymongo==4.7.3 \
    httpx==0.27.2 \
    prometheus-fastapi-instrumentator==7.0.0

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
