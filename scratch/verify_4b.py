import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.core.parser import normalize_filters
from app.core.cache import SimpleCache

def test_normalization():
    print("Testing Query Normalization...")
    f1 = {"gender": "male", "country_id": "NG", "age_group": "adult"}
    f2 = {"country_id": "ng", "gender": "Male", "age_group": "ADULT"}
    
    k1 = normalize_filters(f1)
    k2 = normalize_filters(f2)
    
    print(f"Key 1: {k1}")
    print(f"Key 2: {k2}")
    
    if k1 == k2:
        print("✅ Normalization Success: Keys match.")
    else:
        print("❌ Normalization Failed: Keys differ.")

def test_caching():
    print("\nTesting Simple Cache...")
    cache = SimpleCache(default_ttl=1)
    key = "test_key"
    data = {"foo": "bar"}
    
    cache.set(key, data)
    val = cache.get(key)
    if val == data:
        print("✅ Cache Get Success.")
    else:
        print("❌ Cache Get Failed.")
        
    import time
    time.sleep(1.1)
    val_expired = cache.get(key)
    if val_expired is None:
        print("✅ Cache TTL Success: Item expired.")
    else:
        print("❌ Cache TTL Failed: Item still present.")

if __name__ == "__main__":
    test_normalization()
    test_caching()
