import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class KeyRotator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeyRotator, cls).__new__(cls)
            cls._instance.keys = settings.GOOGLE_API_KEYS
            cls._instance.current_index = 0
            if not cls._instance.keys or cls._instance.keys == ['']:
                logger.warning("No GOOGLE_API_KEYS found in settings.")
        return cls._instance

    def get_current_key(self):
        if not self.keys or self.keys == ['']:
            return None
        return self.keys[self.current_index]

    def rotate(self):
        if not self.keys or len(self.keys) <= 1:
            logger.warning("No alternate keys available for rotation.")
            return False
        
        self.current_index = (self.current_index + 1) % len(self.keys)
        logger.info(f"Rotated to API key index {self.current_index}")
        return True

key_rotator = KeyRotator()
