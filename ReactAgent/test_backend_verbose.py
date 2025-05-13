#!/usr/bin/env python3
import socketio
import time
import json
import sys
from datetime import datetime

# Create a Socket.IO client
sio = socketio.Client(logger=True, engineio_logger=True)

# Generic event handler to catch all events
@sio.on('*')
def catch_all(event, data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Received event '{event}': {json.dumps(data, indent=2)}")

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection success: {json.dumps(data, indent=2)}")

@sio.on('agent_step')
def on_agent_step(data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent step: {json.dumps(data, indent=2)}")

@sio.on('agent_error')
def on_agent_error(data):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent error: {json.dumps(data, indent=2)}")

def send_message(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending message: '{message}'")
    sio.emit('chat_message', {'message': message})
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Message sent. Waiting for response...")

def main():
    try:
        # Connect to the server
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to connect to server at http://localhost:5001")
        sio.connect('http://localhost:5001')
        
        # Wait for connection
        time.sleep(2)
        
        if len(sys.argv) > 1:
            # Use command line argument as message
            message = ' '.join(sys.argv[1:])
            send_message(message)
            time.sleep(25)  # Wait for response
        else:
            # Interactive mode
            print("Connected to server. Type 'exit' to quit.")
            while True:
                message = input("Enter message to send (or 'exit'): ")
                if message.lower() == 'exit':
                    break
                send_message(message)
                time.sleep(2)  # Short pause between messages
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
    finally:
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    main() 