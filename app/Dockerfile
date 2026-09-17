FROM python:3.12-slim

WORKDIR /opt/marketpulse

ENV PYTHONPATH=/opt/marketpulse

RUN apt-get update && apt-get install -y libsqlite3-mod-spatialite

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.6 \
    asyncpg==0.29.0 \
    redis==5.0.8 \
    motor==3.5.1 \
    pymongo==4.7.3 \
    httpx==0.27.2 \
    prometheus-fastapi-instrumentator==7.0.0 \
    aiosqlite==0.20.0 \
    ZODB==6.0.0 \
    duckdb==1.0.0 \
    email-validator==2.1.1 \
    PyJWT==2.8.0 \
    passlib==1.7.4 \
    bcrypt==4.1.2 \
    python-multipart==0.0.12

COPY . /opt/marketpulse/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
