import pandas as pd
from sqlalchemy import create_engine

db_url = "postgresql://marketpulse:marketpulse_password_1122@192.168.1.123:5432/marketpulse"
try:
    engine = create_engine(db_url)
    cols = pd.read_sql(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'", engine
    )
    print("Tables:", cols["table_name"].tolist())
except Exception as e:
    print(e)
