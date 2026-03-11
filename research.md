# Research

## 목적

이 문서는 현재 저장소가 정확히 어떻게 동작하는지, 그리고 웹앱 전환 작업과 직접 관련된 구조가 무엇인지 기록한다. 목표는 기존 시스템을 파괴하거나 중복 구현하지 않고, legacy 엔진을 새 아키텍처로 옮길 때 필요한 맥락을 남기는 것이다.

## 1. 현재 저장소의 두 축

현재 저장소는 사실상 두 개의 시스템이 공존한다.

### A. legacy single-user trading bot

- 경로: `config/`, `src/`, `tests/`
- 형태: 로컬에서 실행하는 Python asyncio 봇
- 사용자 모델: 단일 사용자
- 인증 모델: `.env`에 개인키를 넣고 서버 프로세스가 직접 거래
- 상태 저장: 메모리 + `logs/` JSON 파일

### B. new web app scaffolding

- 경로: `frontend/`, `api/`, `worker/`, `shared/`
- 형태: 웹앱 전환을 위한 초기 골격
- 사용자 모델: 사용자별 세션과 bot config를 가정
- 인증 모델: nonce sign-in + session
- 상태 저장: API에서 SQLite 기반 초기 persistence

현재 실제 동작이 완성된 쪽은 A이고, B는 구조와 기초 흐름을 잡아 놓은 상태다.

추가 상태 메모:

- 문서 기준선(`README.md`, `research.md`, `plan.md`)이 이제 저장소 루트에 존재한다.
- 사용자 승인 후 다음 구현 단계는 frontend의 실제 wallet sign-in이다.

## 2. legacy bot 분석

### 2.1 진입점과 전체 루프

핵심 진입점은 `src/main.py` 이다.

주요 역할:

- `MarketStore` 생성
- `PriceHistory` 생성
- `EnsembleStrategy` 생성
- `GammaClient` 로 거래 가능한 마켓 조회
- `MarketWebSocket` 으로 실시간 가격 수신
- `Trader` 로 paper/live 실행 분기
- 5초마다 전체 시장 평가
- 실시간 가격 업데이트 시 즉시 exit 체크

즉, 구조는 다음과 같다.

1. 시작 시 Gamma API로 활성 마켓 목록 적재
2. 각 token을 store에 등록
3. websocket으로 호가/가격 수신
4. 수신 데이터로 `MarketStore`, `PriceHistory` 갱신
5. 주기적으로 전략 평가
6. 진입/청산 주문 실행
7. 결과와 상태를 저장

### 2.2 데이터 계층

#### `src/data/market_store.py`

역할:

- token별 현재 시장 상태 보관
- `condition_id -> outcome -> token_id` 매핑 유지
- orderbook, best bid/ask, mid price, last trade, price update time 관리

핵심 포인트:

- 실시간 메시지를 직접 해석하는 `handle_ws_message` 가 있다.
- 차익거래 전략은 `condition_id` 기준으로 YES/NO 쌍을 찾는다.
- 가격 갱신 시점 `price_updated_at` 이 있어 stale data 필터에 사용된다.

#### `src/data/price_history.py`

역할:

- token별 최근 가격/거래량 deque 유지
- 모멘텀 전략에서 RSI/BB/EMA 계산의 입력으로 사용

제약:

- 영속화 없음
- 프로세스 재시작 시 히스토리 초기화

### 2.3 전략 계층

#### `src/strategy/base.py`

- `Signal` 데이터 구조 제공
- 모든 전략은 `evaluate()` 형태를 따른다

#### `src/strategy/orderbook_imbalance.py`

원리:

- 상위 depth의 bid/ask size를 합산
- `(bid - ask) / total` 로 imbalance 계산
- threshold 초과 시 BUY/SELL signal 생성

문제/특성:

- 독립적인 외부 알파 없이 orderbook만으로 `estimated_prob` 를 조정한다
- `p_hat = market_price +/- scaled adjustment`
- 즉, EV가 시장 자체에서 파생된다

#### `src/strategy/momentum.py`

원리:

- RSI
- Bollinger Band
- EMA crossover
- 3개 중 2개 이상 합의 시 signal

문제/특성:

- 예측시장 가격이 이벤트 기반이라는 점에서 기술지표의 의미가 약할 수 있다
- 그래도 구현상으로는 정상적인 indicator pipeline 이다

#### `src/strategy/arbitrage.py`

원리:

- 같은 condition의 YES/NO ask 합이 1보다 충분히 낮으면 차익 탐지

보완사항:

- midpoint가 아닌 best ask 사용
- stale price 배제
- spread 필터 있음
- sum이 너무 낮으면 데이터 이상으로 간주

#### `src/strategy/ensemble.py`

원리:

- directional signal은 orderbook + momentum 결합
- 둘 중 하나 또는 둘 다 signal을 내도 side가 일치해야 함
- strength와 EV는 가중/평균 처리
- arbitrage는 별도 경로로 반환

결론:

- 현재 전략 핵심은 "market mispricing 추정"이지 "시장 추종"은 아니다
- 사용자가 새 방향으로 제시한 `market_follow` 전략과는 성격이 다르다

### 2.4 실행 및 리스크 계층

#### `src/execution/risk.py`

역할:

- Kelly fraction 계산
- bet size 계산
- trade 허용 여부 판정
- open position 관리
- exit condition 판정

핵심 규칙:

- EV threshold
- 최대 포지션 수
- 일일 손실 제한
- 재진입 cooldown
- mid-price zone 회피
- 손절 / 익절 / trailing stop / max hold / stale exit / price gap exit

중요한 설계 사실:

- `RiskManager` 는 현재 메모리 기반이며 JSON state file에 저장한다
- DB나 ORM은 없다

#### `src/execution/paper.py`

역할:

- paper trading fill, bankroll, trade history 관리
- slippage와 fee 반영
- unrealized / realized pnl 분리

상태 저장:

- `logs/paper_state.json`
- `logs/paper_trades_*.json`

#### `src/execution/trader.py`

역할:

- BUY/SELL signal 실행
- live/paper 분기
- arbitrage 실행
- fill 검증
- 고스트 포지션 정리

설계적 의미:

- 실제 전략과 CLOB 주문 사이의 adapter 역할
- 새 worker 구조로 옮길 때 재사용 가치가 높음

### 2.5 외부 클라이언트 계층

#### `src/client/gamma.py`

- Polymarket Gamma API로 활성 마켓을 가져온다
- REST 조회용
- 공개 시장 데이터 discovery 역할

#### `src/client/websocket.py`

- Polymarket market websocket 구독
- orderbook/price change 실시간 수신
- reconnect loop 있음

#### `src/client/clob.py`

- `py-clob-client` wrapper
- limit order, market order, fill 확인, 잔고/allowance 조회

중요:

- 개인키 기반 인증을 직접 수행한다
- `create_or_derive_api_creds()` 호출
- 따라서 현재 구조는 서버 프로세스가 거래 권한을 가진다

이 점이 웹앱 전환의 핵심 차이점이다.

### 2.6 설정과 부가 기능

#### `config/settings.py`

- pydantic settings 기반
- private key, funder, signature type, risk params, fee/slippage, telegram, API URL 관리

#### `src/utils/telegram.py`

- 텔레그램 알림
- buy/sell/arbitrage 및 세션 요약 전송

### 2.7 테스트 구조

테스트는 다음에 집중되어 있다.

- `tests/test_strategies.py`
- `tests/test_paper_trader.py`
- `tests/test_risk.py`

테스트 의미:

- 핵심 계산 로직은 검증돼 있음
- 하지만 API / persistence / frontend / worker runtime 테스트는 아직 없음

### 2.8 기존 시스템의 구조적 한계

웹앱 전환 관점에서 중요한 한계:

1. 단일 사용자 설계
2. 개인키를 서버 환경변수로 받음
3. DB/ORM 없음
4. API 서버 없음
5. 세션/권한 모델 없음
6. UI 없음
7. worker 분리 없음

즉, 기존 코드는 "전략 엔진"이지 "제품 백엔드"는 아니다.

## 3. 새 web app 구조 분석

### 3.1 frontend

주요 파일:

- `frontend/app/page.tsx`
- `frontend/app/app/page.tsx`
- `frontend/components/dashboard.tsx`
- `frontend/lib/api.ts`

현재 상태:

- 랜딩 페이지 존재
- 대시보드 페이지 존재
- API health check 가능
- wagmi provider와 injected wallet connector 추가
- nonce 요청 / sign message / verify / session 조회 / bot 생성 / bot 목록 / bot start 흐름 UI 존재

한계:

- worker runtime과 아직 연결되지 않음
- 실제 브라우저 실행 검증은 아직 안 함
- 스타일은 기본 MVP 수준

### 3.2 api

주요 파일:

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

현재 상태:

- FastAPI app 존재
- startup 시 SQLite schema 초기화
- nonce 발급 가능
- EVM signature 검증 로직 준비
- session token 발급/조회/로그아웃 가능
- bot config 생성/조회/수정 가능
- bot run 기록 생성 가능

중요한 사실:

- ORM은 아직 없다
- 현재 persistence는 sqlite3 직접 사용이다
- 서비스 레이어가 있으므로 나중에 SQLAlchemy로 교체 가능

### 3.3 worker

주요 파일:

- `worker/app/main.py`
- `worker/app/runtime/manager.py`
- `worker/app/runtime/runtime.py`
- `worker/app/strategies/market_follow.py`
- `worker/app/execution/paper_executor.py`

현재 상태:

- runtime manager singleton 존재
- API route에서 runtime manager를 직접 호출하는 방식으로 연결됨
- bot start 시 background thread가 생성되고 5초마다 heartbeat를 남김
- run status와 event log를 DB에 기록
- `PaperExecutor` 는 매우 얇은 placeholder 상태
- 실제 market data / order execution 연결 없음

### 3.4 shared

주요 파일:

- `shared/python/shared/domain/models.py`
- `shared/python/shared/strategy/base.py`

현재 상태:

- API와 worker에서 공통으로 쓸 계약 정의 시작
- bot config / run / position / event 모델 존재
- strategy interface 존재

한계:

- legacy `Signal`, `PositionInfo`, settings와 아직 통합되지 않음

## 4. 레이어 구조와 ORM/데이터 관리 방식

### legacy

- 레이어는 사실상 `client -> data -> strategy -> execution -> main`
- ORM 없음
- JSON 파일 기반 state persistence

### new api

- `routes -> services -> db`
- ORM 없음
- sqlite3 직접 사용

이 상태의 장점:

- 빠르게 시작 가능

이 상태의 단점:

- query 조합이 많아지면 유지보수 어려움
- migration tooling 없음
- 테스트 fixture 설계가 빈약함

따라서 다음 단계에서 판단해야 할 것:

- 계속 sqlite3로 갈지
- SQLAlchemy + Alembic로 조기 전환할지

현재 제품 방향상, 사용자/봇/런/주문/포지션이 늘어날 것이므로 장기적으로는 ORM 도입이 유리하다.

## 5. 이미 존재하는 API 엔드포인트

현재 `api` 기준 엔드포인트:

- `GET /health`
- `POST /auth/nonce`
- `POST /auth/verify`
- `GET /auth/me`
- `POST /auth/logout`
- `GET /bots`
- `POST /bots`
- `GET /bots/{bot_id}`
- `PATCH /bots/{bot_id}`
- `POST /bots/{bot_id}/start`
- `POST /bots/{bot_id}/stop`
- `GET /runs`
- `GET /runs/{run_id}`

현재 부족한 것:

- markets API
- positions API
- orders API
- worker 상태 API
- live trading credential 관리 API

## 6. 구현 대상 기능과 직접 연관된 조사 결론

사용자가 원하는 최종 형태는:

- 웹앱
- 월렛 연결
- 실제 알고리즘 거래

이 목표를 위해 지금 필요한 것은 전략 자체보다 다음이다.

1. 사용자 인증
2. bot 설정 저장
3. worker와 api 연결
4. market_follow 전략 런타임 구현
5. paper trading end-to-end
6. 이후 live trading 연결

중요한 제품 판단:

- 지금 바로 live trading 으로 가면 인증/권한/credential 저장 문제가 같이 폭발한다
- 따라서 `paper trading 완성 -> live trading 확장` 순서가 안전하다

## 7. 새로 발견된 사실 / 수정 이력

### 최신 상태

- web app 전환 설계 문서가 이미 추가되어 있다
  - `docs/WEBAPP_ARCHITECTURE.md`
  - `docs/MIGRATION_PLAN.md`
- API는 더 이상 완전한 스텁이 아니고, SQLite persistence 초안이 들어갔다
- frontend는 wagmi 기반 월렛 연결과 sign message 인증 흐름 초안을 가진다
- API는 localhost 프론트 연결을 위한 CORS 설정이 들어갔다
- worker runtime은 현재 별도 프로세스가 아니라 API 프로세스 내부 background thread MVP로 동작한다
- run 상태 추적을 위해 `bot_runs.last_heartbeat_at` 와 `event_logs` 테이블이 추가되었다
- 문서 기준선 파일(`README.md`, `research.md`, `plan.md`)이 추가되었고, 이후 작업은 이 문서를 기준으로 진행해야 한다

### 아직 틀리거나 미완인 부분

- worker는 시장 데이터와 주문 실행이 아직 비어 있다
- frontend는 wallet SDK 연결 초안이 있으나 실제 브라우저 검증은 안 했다
- API signature verify는 코드상 존재하지만, 실실행 검증은 아직 안 했다
- 저장 계층은 ORM 없이 sqlite3 직접 접근이다

## 8. 다음 조사 필요 영역

이후 구현 전에 추가 조사해야 할 것:

1. Polymarket live credential 저장 모델
2. wagmi/viem 기반 프론트 서명 흐름
3. worker와 api 간 queue 또는 direct runtime control 방식
4. paper trade 결과를 DB로 남기는 스키마

## 업데이트 규칙

새로운 사실을 발견하거나 기존 판단이 틀린 것이 확인되면 이 파일을 즉시 갱신해야 한다. 특히 아래는 반드시 반영한다.

- worker가 실제로 legacy 코드를 흡수하기 시작했을 때
- ORM 도입 여부가 결정되었을 때
- live trading credential 모델이 바뀌었을 때
- frontend wallet UX가 구현되었을 때
