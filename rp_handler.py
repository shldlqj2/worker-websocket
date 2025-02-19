from websocket_server import WebsocketServer
import runpod
import os 

def on_new_client(client, server):
    """Handle new client connection."""
    print(f"New client connected: {client['id']}")

def on_message(client, server, message):
    """Handle incoming messages from clients."""
    print(f"Received: {message}")
    server.send_message(client, f"Echo: {message}")

def on_client_left(client, server):
    """Handle client disconnection."""
    print(f"Client {client['id']} disconnected")

def handler(event):
    input = event['input']
    
    public_ip = os.environ.get('RUNPOD_PUBLIC_IP', 'localhost')  # Default to 'localhost' if not set
    tcp_port = int(os.environ.get('RUNPOD_TCP_PORT_8765', '8765')) 
    
    print(f"Public IP: {public_ip}")  
    print(f"TCP Port: {tcp_port}")  
    
    progress_data = {
        "public_ip": public_ip,
        "tcp_port": tcp_port
    }
    
    # runpod.serverless.progress_update(progress_data, f"Public IP: {public_ip}, TCP Port: {tcp_port}")
    # 

    prompt = input.get('prompt', 'Start Streaming')  
    seconds = input.get('seconds', 0)  

    server = WebsocketServer(host="0.0.0.0", port=8765)
    # Bind events
    server.set_fn_new_client(on_new_client)
    server.set_fn_client_left(on_client_left)
    server.set_fn_message_received(on_message)

    print("WebSocket server started on port 8765...")
    server.run_forever()
    # return prompt 

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})