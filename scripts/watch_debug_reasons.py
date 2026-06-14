import asyncio
from application.core.event_bus import bus

async def main():
    collected = []

    async def handler(payload):
        print("REASON EVENT:", payload)

    await bus.start()
    await bus.subscribe('RESPONSE_READY_META', handler)
    print('Listening for RESPONSE_READY_META events. Press Ctrl-C to exit.')
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print('Stopping...')
    finally:
        try:
            await bus.unsubscribe('RESPONSE_READY_META', handler)
            await bus.stop()
        except Exception:
            pass

if __name__ == '__main__':
    asyncio.run(main())
