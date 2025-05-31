# someip_protocol.py
# SOME/IP message handling functions

import struct
from constants import SERVICE_ID, METHOD_ID, CLIENT_ID, SESSION_ID, PROTOCOL_VERSION, INTERFACE_VERSION, RESPONSE_TYPE

def parse_someip_header(header_data):
    """Parse a SOME/IP header from binary data."""
    service_id, method_id, client_id, session_id, protocol_version, interface_version, message_type, payload_length = struct.unpack(
        '!HHHHBBBxI', header_data
    )
    
    return {
        'service_id': service_id,
        'method_id': method_id,
        'client_id': client_id,
        'session_id': session_id,
        'protocol_version': protocol_version,
        'interface_version': interface_version,
        'message_type': message_type,
        'payload_length': payload_length
    }

def create_someip_response(payload, service_id=SERVICE_ID, method_id=METHOD_ID, 
                          client_id=CLIENT_ID, session_id=SESSION_ID,
                          protocol_version=PROTOCOL_VERSION, 
                          interface_version=INTERFACE_VERSION):
    """Create a SOME/IP response message."""
    payload_length = len(payload)
    
    header = struct.pack(
        "!HHHHBBBxI",
        service_id, method_id, client_id, session_id,
        protocol_version, interface_version, RESPONSE_TYPE, payload_length
    )
    
    return header + payload

def decode_payload(payload):
    """Try to decode the payload as UTF-8 text."""
    try:
        return payload.decode('utf-8')
    except UnicodeDecodeError:
        return "<Binary Data>"