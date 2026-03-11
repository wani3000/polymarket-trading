from worker.app.runtime.runtime import BotRuntime


class RuntimeManager:
    """Coordinates active bot runtimes.

    This is the replacement entry point for the old single-process bot.
    """

    def __init__(self) -> None:
        self._runtimes: dict[str, BotRuntime] = {}

    def run_forever(self) -> None:
        print("worker runtime manager started")

    def start_runtime(self, bot_id: str) -> None:
        if bot_id in self._runtimes:
            return
        self._runtimes[bot_id] = BotRuntime(bot_id=bot_id)

    def stop_runtime(self, bot_id: str) -> None:
        self._runtimes.pop(bot_id, None)
