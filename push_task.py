import os
import sys

sys.path.append(r"c:\marketpulse\MarketPulse")

os.environ["RABBITMQ_URL"] = "amqp://marketpulse:marketpulse_password_1122@localhost:5673//"

from workers.presentation.tasks import fetch_market_data_task

print("Pushing normal task AAPL...")
r1 = fetch_market_data_task.delay("AAPL")
print(f"Task pushed! Task ID: {r1.id}")
try:
    print(f"Task result: {r1.get(timeout=10)}")
except Exception as e:
    print(f"Task AAPL failed: {e}")

print("Pushing failure task ERROR...")
r2 = fetch_market_data_task.delay("ERROR")
print(f"Task pushed! Task ID: {r2.id}")
try:
    print(f"Task result: {r2.get(timeout=15)}")
except Exception as e:
    print(f"Task ERROR failed: {e}")

print("Checking task states:")
print(f"AAPL state: {r1.state}")
print(f"ERROR state: {r2.state}")
