# Plan

## 목적

이 문서는 web app 전환 작업의 실행 설계도다. `research.md` 를 기반으로 어떤 파일을 어떤 순서로 바꿀지 기록하고, 이후 피드백과 방향 수정 이력을 남긴다.

현재 원칙:

- 추가 코드 수정은 이 계획을 기준으로 진행한다.
- 전략은 당분간 `market_follow` 단일 전략으로 둔다.
- 우선순위는 `제품 구조 완성 > 전략 고도화` 이다.
- `paper trading` 을 먼저 완성한 뒤 `live trading` 으로 간다.

## 문제 해결 전략

### 핵심 접근

legacy 엔진을 한 번에 지우지 않는다. 대신 새 아키텍처를 먼저 세우고, legacy에서 재사용 가능한 모듈을 worker로 단계적으로 옮긴다.

전략:

1. frontend, api, worker, shared의 경계를 먼저 고정
2. 사용자 인증과 bot persistence를 api에서 먼저 안정화
3. worker runtime을 만들어 사용자별 봇 루프를 수용
4. legacy의 시장 데이터/리스크/실행 로직을 worker로 추출
5. paper trading end-to-end를 붙인 뒤 live trading으로 확장

### 왜 이런 순서인가

- frontend만 먼저 만들면 실행 엔진이 없어 빈 UI가 된다
- worker만 먼저 만들면 사용자/세션/설정 개념이 없어 제품이 되지 않는다
- live trading을 먼저 붙이면 credential과 보안 이슈 때문에 전체 구조가 흔들린다

## 현재 아키텍처 목표

```text
frontend -> api -> worker -> Polymarket
                 |
                 -> database
```

## 구현 계획

### Phase 0. 문서 기준선

대상 파일:

- `README.md`
- `research.md`
- `plan.md`

목표:

- 다른 에이전트가 바로 합류 가능한 상태 만들기

상태:

- 진행 중인 요청으로 반영 중

### Phase 1. API 인증과 persistence

대상 파일:

- `api/app/main.py`
- `api/app/config.py`
- `api/app/db/init.py`
- `api/app/db/session.py`
- `api/app/dependencies.py`
- `api/app/services/auth_service.py`
- `api/app/services/bot_service.py`
- `api/app/routes/auth.py`
- `api/app/routes/bots.py`
- `api/app/routes/runs.py`

목표:

- nonce sign-in
- session 조회
- bot 생성/조회/수정
- bot run 생성

현재 상태:

- 초기 구현 완료
- 실실행 검증과 보완 필요

의사코드:

```python
def issue_nonce(wallet):
    nonce = random_nonce()
    save_nonce(wallet, nonce, expires_at=10m)
    return message_for_signature(wallet, nonce)

def verify_signature(wallet, message, signature):
    issued = load_nonce(wallet)
    assert issued.message == message
    recovered = recover_address(message, signature)
    assert recovered == wallet
    user = get_or_create_user(wallet)
    session = create_session(user)
    delete_nonce(wallet)
    return session
```

트레이드오프:

- 지금은 sqlite3 직접 접근으로 빠르게 구현
- 장기적으로는 SQLAlchemy 전환 가능성이 높음

### Phase 2. frontend 월렛 흐름

대상 파일:

- `frontend/package.json`
- `frontend/app/app/page.tsx`
- `frontend/components/dashboard.tsx`
- `frontend/lib/api.ts`

목표:

- 브라우저에서 월렛 연결
- nonce 발급
- 서명
- session 저장
- bot 생성

현재 상태:

- 수동 입력 기반 대시보드 골격 완료
- 실제 wallet SDK 연결 미완

의사코드:

```tsx
const { address } = useAccount()

async function signIn() {
  const nonce = await api.post("/auth/nonce", { wallet_address: address })
  const signature = await walletClient.signMessage({ message: nonce.message })
  const session = await api.post("/auth/verify", {
    wallet_address: address,
    message: nonce.message,
    signature,
  })
  saveSession(session)
}
```

트레이드오프:

- wagmi/viem 도입 시 프론트 의존성이 늘어난다
- 하지만 실제 월렛 UX를 위해 사실상 필요하다

### Phase 3. worker runtime

대상 파일:

- `worker/app/main.py`
- `worker/app/runtime/manager.py`
- `worker/app/runtime/runtime.py`
- `worker/app/strategies/market_follow.py`
- 신규: `worker/app/market/*`
- 신규: `worker/app/execution/*`
- 신규: `worker/app/clients/*`

목표:

- 사용자별 봇 런타임 생성
- bot start/stop 수용
- market_follow 전략 평가 루프
- paper trade 상태 저장

의사코드:

```python
class BotRuntime:
    def __init__(self, bot_config):
        self.config = bot_config
        self.store = MarketStore()
        self.history = PriceHistory()
        self.strategy = MarketFollowStrategy()
        self.risk = RiskManager.from_config(bot_config)
        self.executor = PaperExecutor()

    async def run(self):
        await self.load_markets()
        await self.connect_ws()
        while True:
            signals = self.strategy.evaluate_all(self.store, self.history)
            approved = self.risk.filter(signals)
            await self.executor.execute(approved)
            await sleep(5)
```

트레이드오프:

- legacy 코드를 최대한 재사용하면 빠르다
- 그러나 `src/main.py` 구조를 그대로 가져오면 multi-user runtime으로 바꾸기 어렵다
- 따라서 loop orchestration은 새로 짜고, 내부 계산 모듈만 재사용하는 것이 낫다

### Phase 4. legacy 추출

이동 또는 재작성 후보:

- `src/client/gamma.py`
- `src/client/websocket.py`
- `src/client/clob.py`
- `src/data/market_store.py`
- `src/data/price_history.py`
- `src/execution/risk.py`
- `src/execution/trader.py`
- `src/execution/paper.py`

원칙:

- 처음에는 복사/적응
- 안정화 후 legacy 삭제 여부 판단

### Phase 5. end-to-end paper trading

목표:

- frontend에서 bot 생성
- start 누르면 worker runtime 시작
- worker가 paper trades 생성
- API와 frontend에서 run/position/order/event 확인

이 단계가 live trading 이전의 제품 MVP다.

### Phase 6. live trading

목표:

- Polymarket credential 등록
- live mode bot 실행
- 주문/체결 동기화

제약:

- 사용자 credential 보관 모델 확정 필요
- 실거래 stop-safe 메커니즘 필요
- 감사 로그 필요

## 변경 대상 파일 목록

### 이미 생성된 새 구조

- `frontend/app/page.tsx`
- `frontend/app/app/page.tsx`
- `frontend/components/dashboard.tsx`
- `frontend/lib/api.ts`
- `api/app/main.py`
- `api/app/config.py`
- `api/app/db/init.py`
- `api/app/db/session.py`
- `api/app/dependencies.py`
- `api/app/services/auth_service.py`
- `api/app/services/bot_service.py`
- `api/app/routes/auth.py`
- `api/app/routes/bots.py`
- `api/app/routes/runs.py`
- `worker/app/main.py`
- `worker/app/runtime/manager.py`
- `worker/app/runtime/runtime.py`
- `worker/app/strategies/market_follow.py`
- `shared/python/shared/domain/models.py`
- `shared/python/shared/strategy/base.py`

### 앞으로 추가될 가능성이 높은 파일

- `api/app/routes/markets.py`
- `api/app/routes/positions.py`
- `api/app/routes/orders.py`
- `api/app/services/run_service.py`
- `worker/app/market/store.py`
- `worker/app/market/history.py`
- `worker/app/execution/paper_executor.py`
- `worker/app/execution/risk.py`
- `worker/app/clients/gamma.py`
- `worker/app/clients/websocket.py`

## 기술적 제약 사항 및 요구사항

- Python 3.11 기준 유지
- legacy와 새 구조가 한동안 공존해야 함
- 현재 worker는 비어 있으므로 API만 완성돼도 제품은 아님
- live trading은 paper trading 완성 전 착수 금지
- README/research/plan은 항상 최신 상태여야 함

## 고려 사항 및 트레이드오프

### sqlite3 vs ORM

- sqlite3 장점: 빠름, 간단함
- sqlite3 단점: 모델 복잡도 증가 시 유지보수 어려움
- 판단:
  - 지금은 sqlite3 유지 가능
  - worker 연동과 order/position/event schema가 늘어나는 시점에 ORM 전환 검토

### legacy 재사용 vs 재작성

- 재사용 장점: 빠름, 검증된 계산 로직 보존
- 재사용 단점: single-user assumptions가 묻어 있음
- 판단:
  - 계산/도메인 로직은 재사용
  - orchestration과 persistence는 재작성

### market_follow 구현 방식

- 단순 추세 추종으로 가면 빠르게 MVP 가능
- 그러나 이후 외부 데이터 전략으로 확장 시 interface가 중요
- 판단:
  - 지금은 `BaseStrategy -> MarketFollowStrategy` 인터페이스를 먼저 고정

## Iteration

### Iteration 1

- 사용자 지시:
  - 먼저 전체 web app 아키텍처를 잡을 것
  - 이후 `frontend / api / worker / shared` 분해 계획을 작성할 것
  - 전략은 현재 단계에서는 참고만 하고, 방향은 `시장 추종` 으로 둘 것

- 반영 결과:
  - `docs/WEBAPP_ARCHITECTURE.md`
  - `docs/MIGRATION_PLAN.md`
  - 새 구조 스캐폴딩 생성

### Iteration 2

- 사용자 지시:
  - 코드 수정 전에 `README.md`, `research.md`, `plan.md` 를 먼저 유지 가능한 문서로 작성할 것

- 반영 결과:
  - 현재 문서 작성 중
  - 추가 구현은 문서 기준선 정리 후 이어감

### Iteration 3

- 비고:
  - 현재 API persistence 초안과 frontend 대시보드 골격은 이미 존재
  - 이후 변경이 생기면 이 섹션에 이전 판단을 남기고 새 판단을 이어서 기록한다

## Todo List

### 승인 전

- [ ] `README.md` 현재 상태 기준으로 정리 완료
  - 담당: Codex
- [ ] `research.md` legacy + new structure 분석 반영
  - 담당: Codex
- [ ] `plan.md` 구현 순서와 트레이드오프 반영
  - 담당: Codex

### 승인 후 실행

- [ ] frontend에 실제 wagmi/viem 월렛 연결 추가
  - 담당: Codex
- [ ] auth verify 흐름을 프론트와 실제 연결
  - 담당: Codex
- [ ] worker runtime에 market_follow 루프 추가
  - 담당: Codex
- [ ] legacy `MarketStore`, `PriceHistory` 를 worker로 추출
  - 담당: Codex
- [ ] paper execution persistence를 API/DB와 연결
  - 담당: Codex
- [ ] start/stop API와 worker runtime manager 연결
  - 담당: Codex
- [ ] markets / positions / orders 조회 API 추가
  - 담당: Codex

## 업데이트 규칙

아래 상황에서는 반드시 이 파일을 갱신한다.

- iteration 피드백이 들어왔을 때
- 계획이 바뀌었을 때
- todo가 완료됐을 때
- 실제 구현이 계획과 달라졌을 때
- 다른 에이전트에게 인계할 때
