import requests

url = "http://192.168.1.134:8085/predict"
payload = {
    "data": [
        {
            "time": "2023-01-01T00:00:00Z",
            "open": 20000.0,
            "high": 21000.0,
            "low": 19000.0,
            "close": 20500.0,
            "volume": 100.0,
        }
    ]
}

response = requests.post(url, json=payload)
print(response.status_code)
print(response.text)
