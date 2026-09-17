import requests

url = "http://192.168.1.134:8085/retrain"

print("Triggering retraining...")
response = requests.post(url)
print(response.status_code)
print(response.text)
