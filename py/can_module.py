import can
from PyQt6.QtCore import QThread, pyqtSignal
import socket
import struct

# SomeIP Constants
SERVICE_ID = 0x1
METHOD_ID = 0x1
CLIENT_ID = 0x0001
SESSION_ID = 0x0001
PROTOCOL_VERSION = 0x01
INTERFACE_VERSION = 0x01
MESSAGE_TYPE = 0x00  # Request
SERVER_IP = "192.168.1.26"
SERVER_PORT = 30490

class CANListener(QThread):
    new_can_message = pyqtSignal(str, str)  # For updating CAN Tab
    new_someip_message = pyqtSignal(str, str)  # For updating SomeIP Tab

    def __init__(self, channel="vcan0", bustype="socketcan"):
        super().__init__()
        self.running = True
        self.channel = channel
        self.bustype = bustype
        self.bus = can.interface.Bus(channel=self.channel, bustype=self.bustype)

    def run(self):
        # Original socket for sending to the server
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
        # New socket for sending to Node-RED locally
        node_red_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        node_red_port = 5005  # You can choose any free port here
    
        while self.running:
            message = self.bus.recv(timeout=1)
            if message:
                msg_id = message.arbitration_id
        
                # Skip processing if the message is a response from SomeIPListener (0x056)
                if msg_id != 0x123:
                    continue
            
                msg_id_hex = hex(message.arbitration_id)
                data = message.data.hex()
                self.new_can_message.emit(msg_id_hex, data)  # Update CAN tab
        
                # Create SomeIP message with the actual CAN data
                payload = data.encode()  
                payload_length = len(payload)
                someip_header = struct.pack(
                    "!HHHHBBBxI",
                    SERVICE_ID, METHOD_ID, CLIENT_ID, SESSION_ID,
                    PROTOCOL_VERSION, INTERFACE_VERSION, MESSAGE_TYPE, payload_length
                )
                someip_message = someip_header + payload
                # Send to original destination
                sock.sendto(someip_message, (SERVER_IP, SERVER_PORT))
            
                # Send to Node-RED locally as well
                someip_id=f"{hex(SERVICE_ID )}{METHOD_ID}"
                self.new_someip_message.emit(someip_id,data)  # Update SomeIP tab

    def stop(self):
        self.running = False
        self.quit()
        self.wait()
    
def send_can_message(message_id,data,channel="vcan0",bustype="socketcan"):
    """Send a CAN message over the bus"""
    try:
        bus = can.interface.Bus(channel=channel, bustype=bustype)
        if isinstance(data, str):
            data = bytes.fromhex(data)
        msg = can.Message(arbitration_id=message_id, data=data, is_extended_id=False)
        bus.send(msg)
        return True
    except Exception as e:
        print(f"Error sending CAN message: {e}")
        return False
