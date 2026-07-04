import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.main import lifespan
from fastapi import FastAPI

async def test():
    async with lifespan(FastAPI()):
        print('OK')

if __name__ == '__main__':
    asyncio.run(test())
