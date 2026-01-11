import asyncio
import os
import sys

# Set env var before any imports
os.environ['MONGO_URI'] = "mongodb://localhost:27017"

# Mock the config module if it's already imported (unlikely here but safe)
if 'config' in sys.modules:
    del sys.modules['config']

from database import db

async def test_db_syntax():
    print("Testing Database Syntax...")
    try:
        print(f"DB Object: {db}")
        print("Syntax check passed.")
    except Exception as e:
        print(f"Syntax Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_db_syntax())
