# server.py
# Main SOME/IP server implementation

import socket
from constants import SERVER_IP, SERVER_PORT, RESPONSE_PORT
from constants import TEMPERATURE_SERVICE_ID, CHECK_TEMPERATURE_METHOD_ID, SET_FAN_SPEED_METHOD_ID
from someip_protocol import parse_someip_header, create_someip_response
from temperature_service import handle_check_temperature, handle_set_fan_speed
from logger import log_received_message, log_sent_response

def run_server():
    """Run the SOME/IP server."""
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind the socket to the server IP and port
    sock.bind((SERVER_IP, SERVER_PORT))
    
    print(f"Listening for SOME/IP messages on {SERVER_IP}:{SERVER_PORT}...")
    print("Available services:")
    print(f"  - Temperature service (ID: 0x{TEMPERATURE_SERVICE_ID:04x})")
    print(f"    - Check Temperature method (ID: 0x{CHECK_TEMPERATURE_METHOD_ID:04x})")
    print(f"      Receives: Temperature value in hex")
    print(f"      Returns: Appropriate fan speed level (0-3)")
    print(f"    - Set Fan Speed method (ID: 0x{SET_FAN_SPEED_METHOD_ID:04x})")
    print(f"      Receives: Fan speed level (0-4)")
    print(f"      Returns: Confirmation of set fan speed")
    
    try:
        while True:
            # Receive data from the client
            data, addr = sock.recvfrom(1024)  # Buffer size is 1024 bytes
            sender_ip, sender_port = addr  # Extract sender's IP
            
            # Extract SOME/IP header (16 bytes)
            someip_header_data = data[:16]
            payload = data[16:]
            
            # Parse the SOME/IP header
            header = parse_someip_header(someip_header_data)
            
            # Log the received message
            log_received_message(addr, header, payload)
            
            # Determine which service and method to handle
            service_id = header['service_id']
            method_id = header['method_id']
            client_id = header['client_id']
            session_id = header['session_id']
            
            # Handle the request based on service and method
            if service_id == TEMPERATURE_SERVICE_ID:
                response_type = "Temperature"
                if method_id == CHECK_TEMPERATURE_METHOD_ID:
                    # Handle temperature check request - returns appropriate fan speed
                    someip_response = handle_check_temperature(client_id, session_id, payload)
                elif method_id == SET_FAN_SPEED_METHOD_ID:
                    # Handle manual fan speed setting
                    someip_response = handle_set_fan_speed(client_id, session_id, payload)
                elif method_id == RESET_TO_AUTO_METHOD_ID:
                    # Handle resetting to automatic control
                    someip_response = handle_reset_to_auto(client_id, session_id)
                else:
                    # Unknown method for the temperature service
                    response_payload = b"UNKNOWN_METHOD"
                    someip_response = create_someip_response(
                        response_payload,
                        service_id=service_id,
                        method_id=method_id,
                        client_id=client_id,
                        session_id=session_id
                    )
                    response_type = "Error"
            else:
                # Default generic response for unknown services
                response_payload = b"UNKNOWN_SERVICE"
                someip_response = create_someip_response(
                    response_payload,
                    service_id=service_id,
                    method_id=method_id,
                    client_id=client_id,
                    session_id=session_id
                )
                response_type = "Error"
            
            # Send the response back to the sender's IP on RESPONSE_PORT
            sock.sendto(someip_response, (sender_ip, RESPONSE_PORT))
            
            # Log the response
            log_sent_response(sender_ip, RESPONSE_PORT, someip_response, response_type)
            
    finally:
        # Close the socket
        sock.close()

if __name__ == "__main__":
    run_server()
