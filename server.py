from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

@app.route('/')
def index():
    return "BussGPT Agent Server Running"

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    # Send a connection success message
    socketio.emit('connection_success', {'status': 'connected'})

@socketio.on('connect_event')
def handle_connect_event():
    logger.info('Received connect_event')
    socketio.emit('connection_success', {'status': 'acknowledged'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

@socketio.on('chat_message')
def handle_message(data):
    message = data.get('message', '')
    logger.info(f"Received message: {message}")
    
    # Simulate agent thinking
    logger.info("Sending thought step 1")
    socketio.emit('agent_step', {'type': 'thought', 'data': 'Processing your request...'})
    time.sleep(1)
    
    logger.info("Sending thought step 2")
    socketio.emit('agent_step', {'type': 'thought', 'data': 'Processing your request...\nAnalyzing data related to your query...'})
    time.sleep(1)
    
    logger.info("Sending thought step 3")
    socketio.emit('agent_step', {'type': 'thought', 'data': 'Processing your request...\nAnalyzing data related to your query...\nFormulating a response based on available information...'})
    time.sleep(1)
    
    # Send the final response
    logger.info("Sending final answer")
    socketio.emit('agent_step', {'type': 'final_answer', 'data': f"I received your message: '{message}'. This is a simulated response from the BussGPT agent."})
    logger.info("Response complete")

if __name__ == '__main__':
    logger.info("Starting BussGPT Agent server on http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 