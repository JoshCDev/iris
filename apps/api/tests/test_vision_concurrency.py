import asyncio
import time

from app.vision.inference import InferenceService


def test_predict_runs_in_executor_not_event_loop(monkeypatch):
    """Inference must not block the event loop (LEAF-010)."""
    loop = asyncio.new_event_loop()
    blocking = {"entered": False}

    def slow_predict(*a, **k):
        blocking["entered"] = True
        time.sleep(0.05)
        return "done"

    async def probe():
        # schedule a timer that should fire while predict is sleeping
        await asyncio.sleep(0.01)
        return "tick"

    async def main():
        task = loop.run_in_executor(None, slow_predict)
        tick = await probe()
        result = await task
        return tick, result

    tick, result = loop.run_until_complete(main())
    assert tick == "tick"
    assert result == "done"
