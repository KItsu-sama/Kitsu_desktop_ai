# Kitsu Core Event Bus

The `EventBus` is the central backbone of the Kitsu architecture. It facilitates fully decoupled, asynchronous communication between all system modules.

## Technical Contract

- **In-Process Only**: The bus is designed for high-performance, single-process execution. It uses `asyncio.gather` for parallel subscriber notification.
- **Strict Response Lock**: Only one module may emit `RESPONSE_READY` per request. The bus enforces this by checking and setting the `ctx.responded` boolean flag.
- **Error Isolation**: Every subscriber is executed in its own protected context. An exception in one module (e.g., a failing logger) will never block other modules or crash the main AI pipeline.

## API Usage

### Subscribing to an Event
```python
from kitsu.core.event_bus import bus

async def my_handler(ctx):
    print(f"Processing: {ctx.text}")

bus.subscribe("INPUT_RECEIVED", my_handler)
```

### Emitting an Event
```python
await bus.emit("PREPROCESS_DONE", ctx)
```

### Unsubscribing
For dynamic components or transient tasks, use `unsubscribe` to prevent memory leaks:
```python
bus.unsubscribe("RESPONSE_READY", my_handler)
```

## Internal Mechanics

### Asynchronous Execution
If a handler is a coroutine (`async def`), it is awaited directly. If it is a synchronous function, it is automatically offloaded to the default `ThreadPoolExecutor` using `loop.run_in_executor`. This ensures that slow I/O or CPU-bound synchronous code never blocks the main event loop.

### Response Locking Logic
When `RESPONSE_READY` is emitted:
1. The bus checks `ctx.responded`.
2. If `True`, the emission is ignored (logged as a debug event).
3. If `False`, `ctx.responded` is set to `True`, and the event is propagated to subscribers.

This mechanism allows the **Cascading Tier Strategy** to work safely: Reflex, SLM, and LLM paths can all be triggered, but the user only receives the fastest/highest-quality response that wins the race.
