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

        token = response.json()["access_token"]

        # 2. Get me
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("http://192.168.1.134:8080/auth/me", headers=headers)
        print("Me status:", response.status_code)
        print("Me data:", response.json())


if __name__ == "__main__":
    asyncio.run(run())
