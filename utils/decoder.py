import logging
import base64
import binascii
import json
import re
import struct
from urllib.parse import unquote

logger = logging.getLogger(__name__)

def decode_quiz_param(encoded_param):
    """
    Decode the quiz parameter using multiple fallback methods.
    
    Args:
        encoded_param (str): The encoded parameter from the QuizBot URL
    
    Returns:
        str: Decoded parameter or None if all decoding attempts fail
    """
    logger.debug(f"Attempting to decode parameter: {encoded_param}")
    
    # URL-decode the parameter first
    try:
        url_decoded = unquote(encoded_param)
        logger.debug(f"URL-decoded parameter: {url_decoded}")
    except Exception as e:
        logger.warning(f"URL decoding failed: {str(e)}")
        url_decoded = encoded_param
    
    # Try different decoding methods
    decoding_methods = [
        standard_base64_decode,
        url_safe_base64_decode,
        custom_base64_decode,
        binary_decode,
        padded_base64_decode,
        reverse_base64_decode,
        telegram_specific_decode
    ]
    
    for method in decoding_methods:
        try:
            result = method(url_decoded)
            if result:
                logger.debug(f"Successfully decoded using {method.__name__}")
                return result
        except Exception as e:
            logger.debug(f"{method.__name__} failed: {str(e)}")
    
    logger.error("All decoding methods failed")
    return None

def standard_base64_decode(encoded_str):
    """Standard Base64 decoding method"""
    try:
        # Add padding if needed
        padding_needed = len(encoded_str) % 4
        if padding_needed:
            encoded_str += '=' * (4 - padding_needed)
            
        decoded = base64.b64decode(encoded_str)
        
        # Try different encodings
        for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252', 'ascii']:
            try:
                return decoded.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # If all encoding attempts fail, return hex
        return decoded.hex()
    except Exception as e:
        logger.debug(f"Standard base64 decode error: {str(e)}")
        return None

def url_safe_base64_decode(encoded_str):
    """URL-safe Base64 decoding method"""
    try:
        # Add padding if needed
        padding_needed = len(encoded_str) % 4
        if padding_needed:
            encoded_str += '=' * (4 - padding_needed)
            
        decoded = base64.urlsafe_b64decode(encoded_str)
        
        # Try different encodings
        for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252', 'ascii']:
            try:
                return decoded.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # If all encoding attempts fail, return hex
        return decoded.hex()
    except Exception as e:
        logger.debug(f"URL-safe base64 decode error: {str(e)}")
        return None

def custom_base64_decode(encoded_str):
    """Custom Base64 decoding for Telegram's specific encoding"""
    try:
        # Add padding if needed
        padding_needed = len(encoded_str) % 4
        if padding_needed:
            encoded_str += '=' * (4 - padding_needed)
        
        # Replace URL-safe characters with standard Base64 chars
        encoded_str = encoded_str.replace('-', '+').replace('_', '/')
        
        try:
            # First try standard decoding
            decoded = base64.b64decode(encoded_str)
        except:
            # If that fails, try with alternative padding
            try:
                # Try without padding
                encoded_str = encoded_str.rstrip('=')
                decoded = base64.b64decode(encoded_str + '==')
            except:
                # Last attempt with manual padding
                padding = 4 - (len(encoded_str) % 4) if len(encoded_str) % 4 != 0 else 0
                encoded_str += '=' * padding
                try:
                    decoded = base64.b64decode(encoded_str)
                except:
                    return None
        
        # Try different encodings
        for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252', 'ascii']:
            try:
                return decoded.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, return hex representation
        return decoded.hex()
    except Exception as e:
        logger.debug(f"Custom base64 decode error: {str(e)}")
        return None

def binary_decode(encoded_str):
    """Try to decode as binary data"""
    try:
        # Convert to bytes if string
        if isinstance(encoded_str, str):
            encoded_bytes = encoded_str.encode('latin-1')
        else:
            encoded_bytes = encoded_str
        
        # Try to interpret as a binary structure
        # This is a simplified approach; actual implementation would depend on the format
        if len(encoded_bytes) >= 4:
            # Try to extract an integer that might represent length or type
            val = struct.unpack('>I', encoded_bytes[:4])[0]
            return f"Binary data (possible header: {val})"
        return None
    except:
        return None

def padded_base64_decode(encoded_str):
    """Try with different padding configurations"""
    try:
        # Try different paddings
        for i in range(4):
            padded = encoded_str + ('=' * i)
            try:
                decoded = base64.b64decode(padded)
                
                # Try different encodings
                for encoding in ['latin-1', 'utf-8', 'iso-8859-1', 'windows-1252', 'ascii']:
                    try:
                        return decoded.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                
                # If all encodings fail, return hex
                return decoded.hex()
            except:
                continue
        return None
    except Exception as e:
        logger.debug(f"Padded base64 decode error: {str(e)}")
        return None

def reverse_base64_decode(encoded_str):
    """Try reversing the string before decoding"""
    try:
        reversed_str = encoded_str[::-1]
        return base64.b64decode(reversed_str).decode('utf-8')
    except:
        return None

def telegram_specific_decode(encoded_str):
    """
    Telegram-specific decoding method based on known patterns
    """
    try:
        # Handle common Telegram encoding patterns
        # Sometimes Telegram uses a specific encoding scheme
        
        # Try to handle byte-by-byte
        result = bytearray()
        i = 0
        while i < len(encoded_str):
            char = encoded_str[i]
            if char == '%' and i + 2 < len(encoded_str):
                try:
                    hex_val = int(encoded_str[i+1:i+3], 16)
                    result.append(hex_val)
                    i += 3
                except:
                    result.append(ord(char))
                    i += 1
            else:
                result.append(ord(char))
                i += 1
        
        # Try different encodings for the resulting bytes
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                decoded = result.decode(encoding)
                return decoded
            except:
                continue
        
        # If all encodings fail, return hex representation
        return result.hex()
    except:
        return None

def decode_quiz_data(decoded_param):
    """
    Parse the decoded parameter to extract quiz data.
    
    Args:
        decoded_param (str): The decoded parameter from the QuizBot URL
    
    Returns:
        dict: Extracted quiz data or None if parsing fails
    """
    logger.debug(f"Attempting to parse quiz data from: {decoded_param}")
    
    try:
        # Try direct JSON parsing
        try:
            data = json.loads(decoded_param)
            logger.debug("Successfully parsed as JSON")
            return data
        except json.JSONDecodeError:
            logger.debug("Direct JSON parsing failed, trying alternative methods")
        
        # Look for JSON-like patterns
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, decoded_param)
        if match:
            try:
                json_str = match.group(0)
                data = json.loads(json_str)
                logger.debug("Successfully parsed JSON from pattern match")
                return data
            except:
                logger.debug("JSON pattern matching failed")
        
        # Try to extract structured data
        # Some formats might use delimiters like |, : or ;
        delimiters = ['|', ':', ';', ',']
        for delimiter in delimiters:
            if delimiter in decoded_param:
                parts = decoded_param.split(delimiter)
                if len(parts) >= 2:
                    logger.debug(f"Found structured data with delimiter: {delimiter}")
                    
                    # Attempt to construct a structured quiz
                    structured_data = {
                        'title': parts[0].strip(),
                        'questions': []
                    }
                    
                    # Process remaining parts as questions/answers
                    for i in range(1, len(parts), 2):
                        if i + 1 < len(parts):
                            question = {
                                'text': parts[i].strip(),
                                'options': [opt.strip() for opt in parts[i+1].split('/')],
                                'correct_option': 0  # Default to first option
                            }
                            structured_data['questions'].append(question)
                    
                    if structured_data['questions']:
                        return structured_data
        
        # If it looks like a hex string, try to decode it
        if all(c in '0123456789abcdefABCDEF' for c in decoded_param):
            try:
                hex_decoded = bytes.fromhex(decoded_param).decode('utf-8')
                return {'raw_data': hex_decoded}
            except:
                pass
        
        # Last resort: return as raw data
        logger.debug("Could not parse structured data, returning as raw")
        return {'raw_data': decoded_param}
    
    except Exception as e:
        logger.error(f"Error parsing quiz data: {str(e)}", exc_info=True)
        return None
