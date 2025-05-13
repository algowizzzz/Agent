#!/usr/bin/env python3
import socketio
import time
import sys

# Create a Socket.IO client with debug logging
sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("\n=== Connected to backend server! ===")
    print("Socket ID:", sio.sid)

@sio.event
def disconnect():
    print("\n=== Disconnected from backend server ===")

@sio.event
def connection_success(data):
    print(f"\n=== Received connection_success: {data} ===")
    
@sio.event
def agent_step(data):
    print(f"\n=== Received agent_step: {data} ===")
    
@sio.event
def agent_error(data):
    print(f"\n=== Received agent_error: {data} ===")

def main():
    try:
        # Connect to the server
        print("\n=== Attempting to connect to backend server... ===")
        sio.connect('http://localhost:5001')
        print("\n=== Connection established. ===")
        
        # Wait 3 seconds after connecting
        time.sleep(3)
        
        # Send a message that should require financial data processing
        print("\n=== Sending financial query message... ===")
        sio.emit('chat_message', {'message': 'What was the price of AAPL on June 14, 2017?'})
        print("\n=== Message sent, waiting for response... ===")
        
        # Wait longer for responses (60 seconds)
        print("\n=== Waiting 60 seconds for response... ===")
        time.sleep(60)
        
    except Exception as e:
        print(f"\n=== Error: {e} ===")
    finally:
        # Disconnect
        if sio.connected:
            print("\n=== Disconnecting... ===")
            sio.disconnect()
        else:
            print("\n=== No active connection to disconnect. ===")

if __name__ == "__main__":
    main() 