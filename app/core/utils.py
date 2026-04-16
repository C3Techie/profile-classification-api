import time
import os
import uuid
from datetime import datetime, timezone

def generate_uuidv7() -> str:
    """Generates a UUID v7 as a string."""
    ts_ms = int(time.time() * 1000)
    
    # rand_a: 12 bits
    rand_a = int.from_bytes(os.urandom(2), 'big') & 0x0FFF
    # rand_b: 62 bits
    rand_b = int.from_bytes(os.urandom(8), 'big') & 0x3FFFFFFFFFFFFFFF
    
    # Construct 128-bit integer
    uuid_int = (ts_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    return str(uuid.UUID(int=uuid_int))

def get_utc_now() -> str:
    """Returns current UTC time in ISO 8601 format with Z suffix."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
