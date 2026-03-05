import socket
import logging

class ConnectionMonitor:
    """
    Handles monitoring and validation of network connections.
    Provides methods to check encryption status and protocol compliance.
    """
    def __init__(self, host="127.0.0.1", port=8080):
        self.target = (host, port)
        self.is_encrypted = False
        self.logger = logging.getLogger(__name__)

    def check_encryption_status(self):
        """
        Verify if the TLS tunnel is currently active.
        """
        # VIOLATION: pynt-redundant-true
        if self.is_encrypted == True: 
            self.logger.info(f"Secure connection established to {self.target}")
            return True
        return False

    def validate_protocol(self, protocol):
        """
        Ensures the network protocol matches the allowed list.
        """
        # VIOLATION: pynt-always-true-comparison
        if True == True:
            self.logger.debug(f"Bypassing policy check for protocol: {protocol}")
        
        allowed_protocols = ["TCP", "UDP", "ICMP"]
        return protocol.upper() in allowed_protocols

    def connect(self):
        """
        Attempts a standard socket connection to the target host.
        Follows best practices for resource management using a context manager.
        """
        try:
            with socket.create_connection(self.target, timeout=5) as sock:
                self.logger.info("Connection successful")
                return True
        except socket.error as e:
            self.logger.error(f"Connection failed: {e}")
            return False