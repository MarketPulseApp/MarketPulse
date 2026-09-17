import asyncio

import httpx


async def run():
    async with httpx.AsyncClient() as client:
        # 1. Login
        response = await client.post(
            "http://192.168.1.134:8080/auth/login",
            data={"username": "test@test.com", "password": "test1234"},
        )
        print("Login status:", response.status_code)
        if response.status_code != 200:
            print(response.text)
            return

        token = response.json()["access_token"]
        print("Got token:", token)

        # 2. Get protected data
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("http://192.168.1.134:8080/market/tick/AAPL", headers=headers)
        print("Tick status:", response.status_code)
        print("Tick data:", response.json())


if __name__ == "__main__":
    asyncio.run(run())
