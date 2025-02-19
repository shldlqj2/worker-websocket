import asyncio
import websockets

async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello")
        response = await websocket.recv()
        print(f"Received: {response}")
        
        # shutdown the server
        await websocket.send("shutdown")
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(client())