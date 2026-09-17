FROM python:3.12-slim

WORKDIR /opt/marketpulse/ml_sidecar

RUN pip install --no-cache-dir \
    fastapi==0.111.0 \
    uvicorn==0.30.1 \
    pydantic==2.7.4 \
    "numpy<2" \
    pandas==2.2.2 \
    scikit-learn==1.5.0 \
    ta==0.11.0 \
    psycopg2-binary==2.9.9 \
    SQLAlchemy==2.0.30

COPY ./ml_sidecar /opt/marketpulse/ml_sidecar/

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8085"]
