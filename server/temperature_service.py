# temperature_service.py
# Temperature service implementation for SOME/IP server
import sys
import struct
import os
from constants import PROTOCOL_VERSION, INTERFACE_VERSION, RESPONSE_TYPE

# Temperature service constants
TEMPERATURE_SERVICE_ID = 0x1
CHECK_TEMPERATURE_METHOD_ID = 0x1
SET_FAN_SPEED_METHOD_ID = 0x2

# Temperature thresholds (in Celsius)
COLD_THRESHOLD = 40.0
NORMAL_THRESHOLD = 90.0
HOT_THRESHOLD = 110.0
CRITICAL_THRESHOLD = 120.0

# Fan speed levels
FAN_SPEEDS = {
    0: "OFF/AUTO",
    1: "LOW",
    2: "MEDIUM",
    3: "HIGH",
    4: "MAX"
}

# Path for control files
FAN_LEVEL_FILE = "/home/user/Desktop/fan_level.txt"
TEMPERATURE_FILE = "/home/user/Desktop/temperature.txt"
MANUAL_OVERRIDE_FILE = "/home/user/Desktop/manual_override.txt"

def parse_temperature_request(payload):
    try:
        # Decode the payload as UTF-8 string
        hex_string = payload.decode('utf-8').strip()
        
        # Check if it starts with '0x' and remove it if present
        if hex_string.startswith('0x'):
            hex_string = hex_string[2:]
        
        # Convert hexadecimal string to integer
        temperature = int(hex_string, 16)
        
        return float(temperature)
    except (UnicodeDecodeError, ValueError):
        # Return a default value if parsing fails
        return 0.0

def is_manual_override_active():
    """Check if manual override is currently active"""
    if os.path.exists(MANUAL_OVERRIDE_FILE):
        with open(MANUAL_OVERRIDE_FILE, "r") as f:
            override = f.read().strip()
            return override == "1"
    return False

def evaluate_temperature(temperature):
    if temperature < COLD_THRESHOLD:
        return 0 
    elif temperature < NORMAL_THRESHOLD:
        return 0
    elif temperature < HOT_THRESHOLD:
        return 1
    elif temperature < CRITICAL_THRESHOLD:
        return 2
    else:
        return 3

def handle_check_temperature(client_id, session_id, payload):
    temperature = parse_temperature_request(payload)
    
    # Write temperature value to file regardless of override status
    with open(TEMPERATURE_FILE, "w") as f:
        f.write(f"{temperature:.1f}")
    
    # Check if manual override is active
    if is_manual_override_active():
        # Read the manually set fan level
        if os.path.exists(FAN_LEVEL_FILE):
            with open(FAN_LEVEL_FILE, "r") as f:
                try:
                    fan_level = int(f.read().strip())
                except ValueError:
                    fan_level = 0
        else:
            fan_level = 0
        print(f"Manual override active - using fan level: {fan_level}")
    else:
        # Calculate automatic fan level based on temperature
        fan_level = evaluate_temperature(temperature)
        # Save automatic fan level
        with open(FAN_LEVEL_FILE, "w") as f:
            f.write(str(fan_level))
        print(f"Automatic control - temperature: {temperature:.1f}°C, fan level: {fan_level}")

    response_payload = struct.pack("!B", fan_level) 
    response_header = struct.pack(
        "!HHHHBBBxI", 
        TEMPERATURE_SERVICE_ID, 
        CHECK_TEMPERATURE_METHOD_ID,
        client_id, 
        session_id,
        PROTOCOL_VERSION, 
        INTERFACE_VERSION, 
        RESPONSE_TYPE, 
        len(response_payload)
    )
    return response_header + response_payload

def handle_set_fan_speed(client_id, session_id, payload):
    import socket
    
    try:
        # Parse the fan speed from the payload (assuming it's a single byte)
        fan_speed = struct.unpack("!B", payload[:1])[0]
        
        # If fan_speed is 0, switch to automatic mode
        # Otherwise, set the fan speed manually
        if fan_speed == 0:
            # Set override flag to 0 (automatic mode)
            with open(MANUAL_OVERRIDE_FILE, "w") as f:
                f.write("0")
            print("Fan speed set to 0 - switching to AUTOMATIC mode")
            
            # Use the latest temperature to calculate the appropriate fan level
            if os.path.exists(TEMPERATURE_FILE):
                try:
                    with open(TEMPERATURE_FILE, "r") as f:
                        temp = float(f.read().strip())
                    auto_fan_level = evaluate_temperature(temp)
                    with open(FAN_LEVEL_FILE, "w") as f:
                        f.write(str(auto_fan_level))
                    fan_speed = auto_fan_level  # Use this for the response
                    print(f"Auto calculated fan speed: {auto_fan_level} for temperature: {temp}°C")
                except (ValueError, FileNotFoundError) as e:
                    print(f"Error reading temperature or calculating auto fan speed: {e}")
            
        else:
            # Save manually set fan speed
            with open(FAN_LEVEL_FILE, "w") as f:
                f.write(str(fan_speed))
            
            # Set manual override flag to 1 (manual mode)
            with open(MANUAL_OVERRIDE_FILE, "w") as f:
                f.write("1")
                
            print(f"Fan speed set to {fan_speed} - switching to MANUAL mode")
            
        # Create response payload for original client
        response_payload = struct.pack("!B", fan_speed)
        
        # Create response header for original client
        response_header = struct.pack(
            "!HHHHBBBxI", 
            TEMPERATURE_SERVICE_ID, 
            SET_FAN_SPEED_METHOD_ID,
            client_id, 
            session_id,
            PROTOCOL_VERSION, 
            INTERFACE_VERSION, 
            RESPONSE_TYPE, 
            len(response_payload)
        )
        
        # Now create a message to send to another client
        # Configure the second client's address
        SECOND_CLIENT_IP = "192.168.1.26"  # Change this to your second client's IP
        SECOND_CLIENT_PORT = 30491         # Change this to your second client's port
        
        # Create a new UDP socket for sending to the second client
        second_client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create a message for the second client (using a new session ID)
        second_client_session_id = (session_id + 1) % 65536  # Increment session ID
        second_client_header = struct.pack(
            "!HHHHBBBxI", 
            TEMPERATURE_SERVICE_ID, 
            SET_FAN_SPEED_METHOD_ID,
            client_id,  # Same client ID for tracking
            second_client_session_id,
            PROTOCOL_VERSION, 
            INTERFACE_VERSION, 
            RESPONSE_TYPE, 
            len(response_payload)
        )
        
        # Combine header and payload for second client
        second_client_message = second_client_header + response_payload
        
        # Send message to second client
        try:
            second_client_sock.sendto(second_client_message, (SECOND_CLIENT_IP, SECOND_CLIENT_PORT))
            mode = "AUTO" if fan_speed == 0 else "MANUAL"
            print(f"Fan speed {fan_speed} (Mode: {mode}) sent to second client at {SECOND_CLIENT_IP}:{SECOND_CLIENT_PORT}")
        except Exception as e:
            print(f"Error sending to second client: {e}")
        finally:
            second_client_sock.close()
        
        # Return the response for the original client
        return response_header + response_payload
        
    except Exception as e:
        print(f"Error in handle_set_fan_speed: {e}")
        # Return default response in case of error
        response_payload = struct.pack("!B", 0)
        response_header = struct.pack(
            "!HHHHBBBxI", 
            TEMPERATURE_SERVICE_ID, 
            SET_FAN_SPEED_METHOD_ID,
            client_id, 
            session_id,
            PROTOCOL_VERSION, 
            INTERFACE_VERSION, 
            RESPONSE_TYPE, 
            len(response_payload)
        )
        return response_header + response_payload

def decode_temperature_response(payload):
    if len(payload) >= 1:  # At least 1 byte for fan level
        fan_level = struct.unpack("!B", payload[:1])[0]
        # Check if this is a manual or automatic fan level
        mode = "MANUAL" if is_manual_override_active() else "AUTO"
        return f"Fan Level: {fan_level} ({FAN_SPEEDS.get(fan_level, 'UNKNOWN')}) - Mode: {mode}"
    return "<Invalid temperature data>"

def decode_fan_speed_response(payload):
    if len(payload) >= 1:  # At least 1 byte for fan speed
        fan_speed = struct.unpack("!B", payload[:1])[0]
        mode = "AUTO" if fan_speed == 0 else "MANUAL"
        return f"Fan Speed Set: {fan_speed} ({FAN_SPEEDS.get(fan_speed, 'UNKNOWN')}) - Mode: {mode}"
    return "<Invalid fan speed data>"