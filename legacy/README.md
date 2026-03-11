# Legacy Code

현재 `config/`, `src/`, `tests/` 는 기존 단일 실행 Python 봇 구현이다.

새 구조가 안정화될 때까지 이 코드는 참조용으로 유지한다.

- 새로운 웹 제품 개발은 `frontend/`, `api/`, `worker/`, `shared/` 기준으로 진행한다.
- 기존 코어 로직은 worker로 단계적으로 옮긴다.
