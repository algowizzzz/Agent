#!/usr/bin/env python3
import socketio
import time
import json
from datetime import datetime

# Create a Socket.IO client
sio = socketio.Client()

# Event handlers
@sio.event
def connect():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected to server!")

@sio.event
def connect_error(error):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection failed: {error}")

@sio.event
def disconnect():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Disconnected from server")

@sio.on('connection_success')
def on_connection_success(data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection success: {data}")

@sio.on('agent_step')
def on_agent_step(data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent step: {json.dumps(data, indent=2)}")

@sio.on('agent_error')
def on_agent_error(data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent error: {json.dumps(data, indent=2)}")

def send_message(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending message: '{message}'")
    sio.emit('chat_message', {'message': message})
    # Give some time for the response to come back
    time.sleep(1)

def main():
    try:
        # Connect to the server
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to connect to server at http://localhost:5001")
        sio.connect('http://localhost:5001')
        
        # Wait for connection
        time.sleep(2)
        
        # Test simple greeting
        send_message("hi")
        time.sleep(3)  # Wait for response
        
        # Test specific query
        send_message("What was the stock price of AAPL on June 15, 2020?")
        
        # Wait for a longer response
        time.sleep(20)
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    main() 