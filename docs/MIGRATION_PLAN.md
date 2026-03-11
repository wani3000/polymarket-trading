# Migration Plan

## Target Layout

```text
polymarket-trading-bot-master/
├── frontend/
├── api/
├── worker/
├── shared/
├── legacy/
└── docs/
```

## Mapping From Current Code

현재 코드는 단일 앱 구조다.

```text
config/
src/
tests/
```

이를 아래처럼 분해한다.

### frontend

새로 만든다.

- 대시보드
- 로그인
- 봇 설정 폼
- 실행 상태 조회

### api

새로 만든다.

- 인증
- 봇 설정 CRUD
- 런 관리
- worker 제어
- read API

### worker

현재 코드의 핵심 재사용 영역이다.

- `src/client/*`
- `src/data/*`
- `src/execution/*`
- `src/strategy/*`
- `src/utils/logger.py`

### shared

현재 코드에서 추출한다.

- 설정 스키마
- 도메인 모델
- 전략 인터페이스
- 이벤트 enum/타입

### legacy

현재 단일 실행 엔트리 보존.

- `src/main.py`
- 기존 README 예제

## Refactor Strategy

큰 리라이트 대신 "추출 후 연결" 방식으로 간다.

### Phase 1

새 폴더 생성과 계약 정의

- `frontend/`
- `api/`
- `worker/`
- `shared/`

### Phase 2

worker 중심 추출

- `MarketStore`, `PriceHistory` 이동
- 전략 베이스와 시장 추종 전략 추가
- `RiskManager`, `Trader` 이동
- `main.py` 의 루프를 `RuntimeManager` 로 재구성

### Phase 3

api 추가

- auth routes
- bot config routes
- run routes
- persistence models

### Phase 4

frontend 추가

- wallet connect
- bot dashboard
- start/stop controls

### Phase 5

legacy 제거 또는 최소 유지

## Initial Shared Package Boundaries

### shared/config

- app settings
- env parsing
- default risk values

### shared/domain

- user
- bot
- run
- order
- position
- event

### shared/strategy

- `StrategySignal`
- `StrategyContext`
- `BaseStrategy`

## Initial Worker Package Boundaries

### worker/clients

- gamma
- clob
- websocket

### worker/market

- market store
- history store
- subscriptions

### worker/strategies

- market_follow
- legacy adapters

### worker/execution

- risk
- trader
- order sync

### worker/runtime

- runtime manager
- bot runtime

## Initial API Package Boundaries

### api/routes

- auth
- bots
- runs
- markets

### api/services

- auth service
- bot service
- run service

### api/db

- models
- session
- migrations

## Initial Frontend Screens

### `/`

- 제품 소개
- 연결 버튼

### `/app`

- 봇 목록
- 현재 실행 상태

### `/app/bots/[id]`

- 전략 설정
- 실행 버튼
- 손익/포지션/로그

## Suggested First Development Milestone

가장 먼저 만들 최소 기능은 아래다.

1. frontend에서 월렛 연결
2. api에서 nonce 인증
3. bot config 생성 API
4. worker에서 mock runtime 시작
5. frontend 대시보드에서 run 상태 표시

이 단계에서는 실제 주문이 없어도 된다.

## Decision Summary

- 엔진 코어는 Python 유지
- 프론트는 Next.js
- 전략은 당분간 market-follow 단일화
- live trading보다 paper trading 우선
- 현재 저장소는 `legacy` 참조 자산으로 단계적 이전
