import asyncio

import websockets


async def test_ws():
    uri = "ws://192.168.1.134:8080/ws/market"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            for _ in range(3):
                message = await websocket.recv()
                print(f"Received: {message[:100]}...")
            print("Successfully received messages!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_ws())
