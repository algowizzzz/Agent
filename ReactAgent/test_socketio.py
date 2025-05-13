#!/usr/bin/env python3
import socketio
import time

# Create a Socket.IO client
sio = socketio.Client()

@sio.event
def connect():
    print('Connection established!')
    # Explicitly send a chat message after connecting
    print('Sending test message...')
    sio.emit('chat_message', {'message': 'Test message with explicit structure'})
    print('Message sent!')

@sio.event
def disconnect():
    print('Disconnected from server')

@sio.on('connection_success')
def on_connection_success(data):
    print(f'Connection success: {data}')

@sio.on('agent_response')
def on_agent_response(data):
    print(f'Received agent response: {data}')

@sio.on('thinking')
def on_thinking(data):
    print(f'Agent is thinking: {data}')

@sio.on('agent_error')
def on_error(data):
    print(f'Agent error: {data}')

try:
    # Connect to the server
    print('Attempting to connect to server...')
    sio.connect('http://localhost:5001')
    
    # Keep the script running for a moment to receive responses
    print('Waiting for responses (10 seconds)...')
    time.sleep(10)  # Wait longer to see responses
    
    # Disconnect
    sio.disconnect()
except Exception as e:
    print(f'Error: {e}') 