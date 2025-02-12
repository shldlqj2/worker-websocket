import runpod
import time  
import os 

def print_env_variables():
    for key, value in os.environ.items():
        print(f"{key}: {value}")  # Print each environment variable

def handler(event):
    input = event['input']
    
    print_env_variables()

    prompt = input.get('prompt', 'Start Streaming')  
    seconds = input.get('seconds', 0)  


    time.sleep(seconds)  

    return prompt 

if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})