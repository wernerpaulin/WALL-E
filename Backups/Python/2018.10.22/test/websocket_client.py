#python3 /home/pi/wall-e/test/websocket_client.py

#!/usr/bin/env python

# WS client example

import asyncio
import websockets

async def hello():
    async with websockets.connect(
            'ws://localhost:8765') as websocket:
        name = input("What's your name? ")

        await websocket.send(name)

        greeting = await websocket.recv()

asyncio.get_event_loop().run_until_complete(hello())
