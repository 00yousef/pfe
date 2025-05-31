import socket
import struct
import threading
from PyQt6.QtCore import QThread, pyqtSignal
import can

# SomeIP Constants
SERVICE_ID = 0x1234
METHOD_ID = 0x9ABC
CLIENT_ID = 0x0001
SESSION_ID = 0x0001
PROTOCOL_VERSION = 0x01
INTERFACE_VERSION = 0x01
MESSAGE_TYPE = 0x00  # Request
SERVER_IP = "192.168.1.26"
SERVER_PORT = 30490
LISTEN_PORT = 30491  # Port to listen for incoming SomeIP messages

class SomeIPListener(QThread):
    new_someip_message = pyqtSignal(str, str)  # For updating SomeIP Tab
    new_can_message = pyqtSignal(str, str,str)  # For updating CAN Tab
    
    def __init__(self, channel="vcan0", bustype="socketcan", listen_port=LISTEN_PORT):
        super().__init__()
        self.running = True
        self.listen_port = listen_port
        self.channel = channel
        self.bustype = bustype
        self.bus = can.interface.Bus(channel=self.channel, bustype=self.bustype)
        
    def run(self):
        # Create UDP socket for listening
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', self.listen_port))
        sock.settimeout(1)  # Set timeout to allow checking self.running
        
        while self.running:
            try:
                # Wait for incoming SomeIP message
                data, addr = sock.recvfrom(1024)
    
                if len(data) >= 16:  # Minimum SomeIP header size
                    # Parse SomeIP header
                    header = data[:16]
                    service_id, method_id, client_id, session_id, \
                    protocol_version, interface_version, message_type, \
                    return_code, payload_length = struct.unpack("!HHHHBBBBI", header)
        
                    # Extract payload
                    payload = data[16:16+payload_length]
                    
                    # Get hex representation of payload
                    payload_hex = payload.hex()
                    can_data_hex=payload.hex()
                    can_data=bytes.fromhex(can_data_hex)
                    # Try to decode as string for display purposes
                    try:
                        payload_str = payload.decode('utf-8', errors='replace')
                    except:
                        payload_str = f"<Binary Data: {payload_hex}>"
        
                    # Emit signal to update SomeIP tab
                    someip_info = f"{hex(service_id)}{method_id}"
                    self.new_someip_message.emit(someip_info, can_data_hex)
        
                    
                    try:
                        # Send to CAN bus
                        msg = can.Message(arbitration_id=0x3, data=can_data, is_extended_id=False)
                        self.bus.send(msg)

                        # Emit to update GUI
                        self.new_can_message.emit("0x3", can_data_hex,"Tx")
                    except Exception as e:
                        print(f"Error forwarding to CAN: {e}")       
            except socket.timeout:
                # This just allows the loop to check self.running periodically
                pass
            except Exception as e:
                print(f"Error in SomeIP listener: {e}")
    
    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class SomeIPClient:
    def __init__(self, server_ip=SERVER_IP, server_port=SERVER_PORT):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP Socket
        
    def send_message(self, message_id, data):
        """
        Send a SOMEIP message
        """
        try:
            # If data is a string, use it as the payload, otherwise use predefined payload
            if isinstance(data, str) and not data.startswith("Predefined"):
                payload = data.encode()
            else:
                payload = b"SOMEIP TEST MESSAGE"
                
            payload_length = len(payload)
            someip_header = struct.pack(
                "!HHHHBBBBI",  # Added return code field (B)
                SERVICE_ID, METHOD_ID, CLIENT_ID, SESSION_ID,
                PROTOCOL_VERSION, INTERFACE_VERSION, MESSAGE_TYPE, 
                0x00,  # Return code (0 = OK)
                payload_length
            )
            someip_message = someip_header + payload
            self.sock.sendto(someip_message, (self.server_ip, self.server_port))
            print(f"[SomeIP] Sent message: ID={message_id}, Payload={payload}")
            return True
        except Exception as e:
            print(f"Error sending SOMEIP message: {e}")
            return False
