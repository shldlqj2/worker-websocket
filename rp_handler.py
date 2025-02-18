import runpod
import time  
import os 

def handler(event):
    input = event['input']
    
    public_ip = os.environ.get('RUNPOD_PUBLIC_IP')  # Default to 'localhost' if not set
    tcp_port = int(os.environ.get('RUNPOD_TCP_PORT_8080')) 
    print(f"Public IP: {public_ip}")  
    print(f"TCP Port: {tcp_port}")  

    prompt = input.get('prompt', 'Start Streaming')  
    seconds = input.get('seconds', 0)  

    time.sleep(seconds)  

    return prompt 

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})