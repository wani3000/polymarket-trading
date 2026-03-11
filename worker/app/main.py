from worker.app.runtime.manager import RuntimeManager


def main() -> None:
    manager = RuntimeManager()
    manager.run_forever()


if __name__ == "__main__":
    main()
