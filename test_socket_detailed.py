import socketio
import time
import sys
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('socket_test')

# Create a Socket.IO client instance
sio = socketio.Client(logger=True, engineio_logger=False)

# Keep track of all received events
received_events = {
    'connection_success': [],
    'agent_response': [],
    'thinking': [],
    'thought': [],
    'action': [],
    'observation': [],
    'error': []
}

# Define event handlers
@sio.event
def connect():
    logger.info("Connected to server!")
    
    # Wait a moment before sending message
    time.sleep(1)
    
    # Send a test question
    question = "What are the main considerations when planning a trip to Japan?"
    logger.info(f"Sending question: {question}")
    sio.emit('chat_message', question)

@sio.event
def disconnect():
    logger.info("Disconnected from server!")
    
    # Print summary of all events received
    logger.info("--- Event Summary ---")
    for event_type, events in received_events.items():
        logger.info(f"{event_type}: {len(events)} events received")
    
    # Print detailed event log
    logger.info("--- Detailed Event Log ---")
    for event_type, events in received_events.items():
        if events:
            logger.info(f"\n{event_type.upper()} EVENTS:")
            for i, event in enumerate(events):
                logger.info(f"  {i+1}. {json.dumps(event, indent=2)}")

@sio.on('connection_success')
def on_connection_success(data):
    logger.info(f"Connection success: {data}")
    received_events['connection_success'].append(data)

@sio.on('agent_response')
def on_agent_response(data):
    logger.info(f"Received agent_response: {data}")
    received_events['agent_response'].append(data)

@sio.on('thinking')
def on_thinking(data):
    logger.info(f"Received thinking: {data}")
    received_events['thinking'].append(data)

@sio.on('thought')
def on_thought(data):
    logger.info(f"Received thought: {data}")
    received_events['thought'].append(data)

@sio.on('action')
def on_action(data):
    logger.info(f"Received action: {data}")
    received_events['action'].append(data)

@sio.on('observation')
def on_observation(data):
    logger.info(f"Received observation: {data}")
    received_events['observation'].append(data)

@sio.on('error')
def on_error(data):
    logger.error(f"Received error: {data}")
    received_events['error'].append(data)

# Connect to the server
try:
    logger.info("Attempting to connect to server...")
    sio.connect('http://localhost:5001', transports=['websocket'])
    
    # Keep the connection open for 60 seconds to receive responses
    timeout = 60
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        remaining = int(timeout - (time.time() - start_time))
        if remaining % 10 == 0:
            logger.info(f"Waiting... {remaining} seconds left")
        time.sleep(1)
    
    # Disconnect from the server
    sio.disconnect()
    
except Exception as e:
    logger.error(f"Error: {e}")
    sys.exit(1) 