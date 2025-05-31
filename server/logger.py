# logger.py
# Logging functions for SOME/IP messages

from constants import TEMPERATURE_SERVICE_ID, CHECK_TEMPERATURE_METHOD_ID, SET_FAN_SPEED_METHOD_ID
from temperature_service import decode_temperature_response, decode_fan_speed_response, FAN_SPEEDS

def log_received_message(addr, header, payload):
    """Log information about a received SOME/IP message."""
    print(f"\nReceived SOME/IP message from {addr}:")
    print(f"  Service ID: 0x{header['service_id']:04x}")
    print(f"  Method ID: 0x{header['method_id']:04x}")
    print(f"  Client ID: 0x{header['client_id']:04x}")
    print(f"  Session ID: 0x{header['session_id']:04x}")
    print(f"  Protocol Version: {header['protocol_version']}")
    print(f"  Interface Version: {header['interface_version']}")
    print(f"  Message Type: {header['message_type']}")
    print(f"  Payload Length: {header['payload_length']}")
    
    # Print the full payload as hex
    print(f"  Raw Payload (Hex): {payload.hex()}")
    
    # Try to decode as text or specific service data
    service_id = header['service_id']
    method_id = header['method_id']
    
    if service_id == TEMPERATURE_SERVICE_ID:
        if method_id == CHECK_TEMPERATURE_METHOD_ID:
            print(f"  Service: Temperature Service")
            print(f"  Method: Check Temperature")
            try:
                temp_hex = payload.decode('utf-8')
                print(f"  Temperature value (hex): {temp_hex}")
                if temp_hex.startswith('0x'):
                    temp_hex = temp_hex[2:]
                temp_value = int(temp_hex, 16)
                print(f"  Temperature value (decimal): {temp_value}°C")
            except (UnicodeDecodeError, ValueError):
                print(f"  Failed to decode temperature value")
        elif method_id == SET_FAN_SPEED_METHOD_ID:
            print(f"  Service: Temperature Service")
            print(f"  Method: Set Fan Speed")
            try:
                if len(payload) >= 1:
                    fan_speed = payload[0]
                    fan_speed_name = FAN_SPEEDS.get(fan_speed, "UNKNOWN")
                    print(f"  Fan speed request: {fan_speed} ({fan_speed_name})")
                else:
                    print(f"  Invalid fan speed request")
            except (IndexError, ValueError):
                print(f"  Failed to decode fan speed value")
    else:
        # Default text decoding for other services
        from someip_protocol import decode_payload
        decoded = decode_payload(payload)
        print(f"  Payload (Decoded): {decoded}")

def log_sent_response(ip, port, response, response_type="Generic"):
    """Log information about a sent SOME/IP response."""
    print(f"Sent SOME/IP {response_type} Response: {response.hex()}")
    
    # If it's a temperature or fan speed response, decode and display the status
    if len(response) > 16:
        header = response[:16]
        payload = response[16:]
        
        # Extract the method ID from the header
        method_id = int.from_bytes(header[2:4], byteorder='big')
        
        if response_type == "Temperature":
            if method_id == CHECK_TEMPERATURE_METHOD_ID:
                status_info = decode_temperature_response(payload)
                print(f"  {status_info}")
            elif method_id == SET_FAN_SPEED_METHOD_ID:
                status_info = decode_fan_speed_response(payload)
                print(f"  {status_info}")
        
    print(f"Response sent to {ip}:{port}")