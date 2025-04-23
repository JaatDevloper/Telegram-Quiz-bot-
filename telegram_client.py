import os
import logging
import telethon
import asyncio
import threading
import base64
import json
import time
import nest_asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from queue import Queue

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class TelegramQuizExtractor:
    def __init__(self):
        """Initialize the Telegram client with API credentials."""
        # API credentials should be provided as environment variables
        try:
            self.api_id = int(os.environ.get('TELEGRAM_API_ID', '0'))
        except ValueError:
            logger.error("Invalid TELEGRAM_API_ID - must be a number")
            self.api_id = 0
            
        self.api_hash = os.environ.get('TELEGRAM_API_HASH', '')
        self.phone = os.environ.get('TELEGRAM_PHONE', '')
        self.session_string = os.environ.get('SESSION_STRING', '')
        
        # Check for required credentials
        if self.api_id == 0 or not self.api_hash:
            logger.warning("Telegram API credentials not provided! Unable to connect to Telegram.")
            self.client_ready = False
            return
        
        # Client state
        self.client = None
        self.client_ready = False
        self.loop = None
        self.thread = None
        
        # Queue for communication between threads
        self.task_queue = Queue()
        self.result_queue = Queue()
        
        # Start the Telegram client in a separate thread
        self._start_client_thread()
    
    def _start_client_thread(self):
        """Start the Telegram client in a separate thread."""
        self.thread = threading.Thread(target=self._run_telegram_client)
        self.thread.daemon = True
        self.thread.start()
        
        # Wait for client to be ready
        timeout = 30  # seconds
        start_time = time.time()
        while not self.client_ready and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        if not self.client_ready:
            logger.warning("Telegram client initialization timed out")
    
    def _run_telegram_client(self):
        """Run the Telegram client in a separate thread with its own event loop."""
        try:
            # Create a new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Create and start the client
            if self.session_string:
                # Use session string if available
                from telethon.sessions import StringSession
                self.client = TelegramClient(StringSession(self.session_string), 
                                          self.api_id, self.api_hash, 
                                          loop=self.loop)
            else:
                # Otherwise use file session
                self.client = TelegramClient('quiz_extractor_session', 
                                          self.api_id, self.api_hash, 
                                          loop=self.loop)
            
            # Define async initialization function
            async def init_client():
                await self.client.start(phone=self.phone)
                logger.info("Telegram client started successfully")
                return True
            
            # Connect and authenticate
            try:
                # Use run_until_complete for async operations
                self.loop.run_until_complete(self.client.connect())
                
                is_authorized = self.loop.run_until_complete(self.client.is_user_authorized())
                if not is_authorized:
                    try:
                        # Initialize client
                        self.client_ready = self.loop.run_until_complete(init_client())
                    except SessionPasswordNeededError:
                        logger.error("Two-factor authentication required but not supported in this version")
                        self.client_ready = False
                    except Exception as e:
                        logger.exception(f"Failed to authenticate: {e}")
                        self.client_ready = False
                else:
                    self.client_ready = True
                    logger.info("Telegram client already authenticated")
            except Exception as e:
                logger.exception(f"Error connecting to Telegram: {e}")
                self.client_ready = False
            
            # Process tasks from queue
            while True:
                if not self.task_queue.empty():
                    task = self.task_queue.get()
                    logger.debug(f"Processing task: {task}")
                    
                    if task['type'] == 'quiz_param':
                        param = task['param']
                        try:
                            # Use run_until_complete for async operations
                            result = self.loop.run_until_complete(self._fetch_quiz_data(param))
                            self.result_queue.put(result)
                        except Exception as e:
                            logger.exception(f"Error fetching quiz data: {e}")
                            self.result_queue.put({'error': f"Error extracting quiz data: {str(e)}"})
                    
                    elif task['type'] == 'shutdown':
                        break
                
                time.sleep(0.1)
            
            # Disconnect client on shutdown
            try:
                is_connected = self.loop.run_until_complete(self.client.is_connected())
                if is_connected:
                    self.loop.run_until_complete(self.client.disconnect())
            except Exception as e:
                logger.exception(f"Error disconnecting client: {e}")
            
        except Exception as e:
            logger.exception(f"Error in Telegram client thread: {e}")
            self.client_ready = False
    
    async def _fetch_quiz_data(self, param):
        """Fetch quiz data from Telegram using the parameter."""
        try:
            logger.info(f"Fetching quiz data for parameter: {param}")
            
            if not self.client_ready:
                return {'error': 'Telegram client not ready'}
            
            # Message the QuizBot with the parameter
            async with self.client.conversation('@QuizBot') as conv:
                await conv.send_message(f"/start {param}")
                
                # Wait for response from the bot
                response = await conv.get_response(timeout=20)
                
                # Process the response
                if response:
                    quiz_data = {
                        'text': response.text,
                        'param': param
                    }
                    
                    # Try to extract more information if available
                    if hasattr(response, 'media') and response.media:
                        quiz_data['has_media'] = True
                    
                    # Get the next messages for more context if any
                    try:
                        next_response = await conv.get_response(timeout=5)
                        if next_response:
                            quiz_data['additional_text'] = next_response.text
                    except Exception:
                        # Timeout is OK - may not have additional messages
                        pass
                    
                    return {
                        'success': True,
                        'quiz_data': quiz_data
                    }
                else:
                    return {'error': 'No response from QuizBot'}
        
        except Exception as e:
            logger.exception(f"Error in _fetch_quiz_data: {e}")
            return {'error': f"Failed to fetch quiz data: {str(e)}"}
    
    def process_quiz_parameter(self, param):
        """Process a quiz parameter extracted from a QuizBot URL."""
        if not self.client_ready:
            return {'error': 'Telegram client not initialized properly'}
        
        try:
            logger.info(f"Processing quiz parameter: {param}")
            
            # Add task to queue
            self.task_queue.put({
                'type': 'quiz_param',
                'param': param
            })
            
            # Wait for result
            timeout = 60  # seconds
            start_time = time.time()
            
            while (time.time() - start_time) < timeout:
                if not self.result_queue.empty():
                    result = self.result_queue.get()
                    return result
                time.sleep(0.5)
            
            return {'error': 'Timeout waiting for quiz data'}
            
        except Exception as e:
            logger.exception(f"Error processing quiz parameter: {e}")
            return {'error': f"Error processing quiz parameter: {str(e)}"}
    
    def cleanup(self):
        """Clean up resources before shutdown."""
        try:
            if self.thread and self.thread.is_alive():
                self.task_queue.put({'type': 'shutdown'})
                self.thread.join(timeout=5)
        except Exception as e:
            logger.exception(f"Error in cleanup: {e}")
