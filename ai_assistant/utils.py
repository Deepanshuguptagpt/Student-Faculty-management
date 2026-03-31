import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class KeyRotator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeyRotator, cls).__new__(cls)
            # Primary: comma-separated list from GOOGLE_API_KEYS setting
            raw_keys = getattr(settings, 'GOOGLE_API_KEYS', [])
            # Filter out empty strings from a bad split
            cls._instance.keys = [k.strip() for k in raw_keys if k.strip()]
            cls._instance.current_index = 0

            if not cls._instance.keys:
                # Fallback: try the standard single-key env var (also used by langchain-google-genai)
                single_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
                if single_key:
                    cls._instance.keys = [single_key]
                    logger.info("KeyRotator: using GOOGLE_API_KEY env var as fallback.")
                else:
                    logger.warning(
                        "No API keys found. Set GOOGLE_API_KEYS in settings (or .env), "
                        "or set GOOGLE_API_KEY environment variable."
                    )
        return cls._instance

    def get_current_key(self):
        if not self.keys:
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
