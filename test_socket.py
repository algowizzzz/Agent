import socketio
import time
import sys

# Create a Socket.IO client instance
sio = socketio.Client(logger=True, engineio_logger=True)

# Define event handlers
@sio.event
def connect():
    print("Connected to server!")
    # Send a test message
    sio.emit('chat_message', 'Test message from Python client')
    print("Sending message: Test message from Python client")
    print("Waiting for responses...")

@sio.event
def disconnect():
    print("Disconnected from server!")

@sio.on('agent_response')
def on_agent_response(data):
    print(f"Received agent_response: {data}")

@sio.on('thinking')
def on_thinking(data):
    print(f"Received thinking: {data}")

@sio.on('thought')
def on_thought(data):
    print(f"Received thought: {data}")

@sio.on('action')
def on_action(data):
    print(f"Received action: {data}")

@sio.on('observation')
def on_observation(data):
    print(f"Received observation: {data}")

@sio.on('connection_success')
def on_connection_success(data):
    print(f"Connection success: {data}")

# Connect to the server
try:
    print("Attempting to connect to server...")
    sio.connect('http://localhost:5001', transports=['websocket'])
    
    # Keep the connection open for 30 seconds to receive responses
    timeout = 30
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        print(f"Waiting... {int(timeout - (time.time() - start_time))} seconds left")
        time.sleep(5)
    
    # Disconnect from the server
    sio.disconnect()
    
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1) 