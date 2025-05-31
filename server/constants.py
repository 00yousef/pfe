# constants.py
# SOME/IP protocol constants

# Network settings
SERVER_IP = '0.0.0.0'  # Listen on all interfaces
SERVER_PORT = 30490
RESPONSE_PORT = 30491  # Port to send responses

# SOME/IP protocol constants
SERVICE_ID = 0x1234  # Generic service ID
METHOD_ID = 0x9ABC   # Generic method ID
CLIENT_ID = 0x0001
SESSION_ID = 0x0001
PROTOCOL_VERSION = 0x01
INTERFACE_VERSION = 0x01
REQUEST_TYPE = 0x00  # Request
RESPONSE_TYPE = 0x80  # Response

# Service IDs
GENERIC_SERVICE_ID = 0x1234
TEMPERATURE_SERVICE_ID = 0x1

# Method IDs
GENERIC_METHOD_ID = 0x9ABC
CHECK_TEMPERATURE_METHOD_ID = 0x1
SET_FAN_SPEED_METHOD_ID = 0x2
RESET_TO_AUTO_METHOD_ID = 0x3