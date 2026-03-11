from worker.app.runtime.manager import RuntimeManager

_manager = RuntimeManager()


def get_runtime_manager() -> RuntimeManager:
    return _manager
