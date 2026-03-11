from __future__ import annotations

from dataclasses import dataclass
from threading import Lock, Thread

from worker.app.runtime.runtime import BotRuntime


@dataclass
class RuntimeHandle:
    runtime: BotRuntime
    thread: Thread


class RuntimeManager:
    """Coordinates active bot runtimes.

    This is the replacement entry point for the old single-process bot.
    """

    def __init__(self) -> None:
        self._runtimes: dict[str, RuntimeHandle] = {}
        self._lock = Lock()

    def run_forever(self) -> None:
        print("worker runtime manager started")

    def start_runtime(self, bot_id: str, run_id: str, user_id: str, config: dict) -> dict:
        with self._lock:
            existing = self._runtimes.get(bot_id)
            if existing and existing.thread.is_alive():
                return {
                    "bot_id": bot_id,
                    "run_id": existing.runtime.run_id,
                    "status": "already_running",
                }

            runtime = BotRuntime(
                bot_id=bot_id,
                run_id=run_id,
                user_id=user_id,
                config=config,
            )
            thread = Thread(
                target=self._run_loop,
                args=(runtime,),
                name=f"bot-runtime-{bot_id[:8]}",
                daemon=True,
            )
            self._runtimes[bot_id] = RuntimeHandle(runtime=runtime, thread=thread)
            thread.start()
            return {"bot_id": bot_id, "run_id": run_id, "status": "starting"}

    def stop_runtime(self, bot_id: str) -> dict:
        with self._lock:
            handle = self._runtimes.get(bot_id)
            if handle is None:
                return {"bot_id": bot_id, "status": "not_running"}
            handle.runtime.stop_event.set()
            return {"bot_id": bot_id, "run_id": handle.runtime.run_id, "status": "stopping"}

    def get_runtime(self, bot_id: str) -> dict | None:
        with self._lock:
            handle = self._runtimes.get(bot_id)
            if handle is None:
                return None
            return {
                "bot_id": handle.runtime.bot_id,
                "run_id": handle.runtime.run_id,
                "user_id": handle.runtime.user_id,
                "ticks": handle.runtime.tick_count,
                "is_alive": handle.thread.is_alive(),
            }

    def _run_loop(self, runtime: BotRuntime) -> None:
        runtime.mark_started()
        try:
            while not runtime.stop_event.is_set():
                runtime.tick()
                runtime.stop_event.wait(5.0)
        finally:
            runtime.mark_stopped()
            with self._lock:
                current = self._runtimes.get(runtime.bot_id)
                if current and current.runtime.run_id == runtime.run_id:
                    self._runtimes.pop(runtime.bot_id, None)
