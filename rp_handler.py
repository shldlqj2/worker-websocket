import asyncio
import websockets
import runpod
import time  
import os 

async def echo(websocket, path):
    async for message in websocket:
        await websocket.send(f"Echo: {message}")

def handler(event):
    input = event['input']
    
    public_ip = os.environ.get('RUNPOD_PUBLIC_IP')  # Default to 'localhost' if not set
    tcp_port = int(os.environ.get('RUNPOD_TCP_PORT_8765')) 
    
    print(f"Public IP: {public_ip}")  
    print(f"TCP Port: {tcp_port}")  
    
    progress_data = {
        "public_ip": public_ip,
        "tcp_port": tcp_port
    }
    
    runpod.serverless.progress_update(progress_data, f"Public IP: {public_ip}, TCP Port: {tcp_port}")

    prompt = input.get('prompt', 'Start Streaming')  
    seconds = input.get('seconds', 0)  

    start_server = websockets.serve(echo, "localhost", 8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

    # return prompt 

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})