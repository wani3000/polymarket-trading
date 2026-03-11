# Polymarket Trading Web App Migration

## 프로젝트 개요

이 저장소는 원래 Polymarket 예측 시장용 단일 사용자 Python 자동매매 봇이었다. 현재는 그 코드를 기반으로, 사용자가 웹에서 월렛을 연결하고 봇을 생성/실행/모니터링할 수 있는 `frontend / api / worker / shared` 구조의 웹앱으로 전환하는 작업이 진행 중이다. 기존 `src/` 중심 엔진은 아직 참조 자산으로 유지되고 있으며, 새 구조는 점진적으로 그 기능을 흡수하는 방식으로 확장하고 있다.

## 현재 작업 컨텍스트

지금 해결하려는 문제는 "로컬에서 내 개인키로 돌리는 단일 봇"을 "웹 UI + 사용자 세션 + 장기 실행 worker" 기반 제품으로 재구성하는 것이다. 전략 자체는 현재 단계에서는 `market_follow` 방향으로 정리하고 있고, 핵심 초점은 전략 고도화보다 시스템 구조 전환이다. 이미 새 디렉토리 골격과 기본 API/프론트가 추가되었지만, 아직 worker 실제 실행 연결과 월렛 서명 UX는 완성되지 않았다.

현재 우선순위:

1. 문서 기준선 정리
2. web app 아키텍처 확정
3. API 인증과 bot persistence 구현
4. frontend 월렛/대시보드 연결
5. worker runtime과 paper execution 연결

## 핵심 디렉토리 구조

- `src/`
  - 기존 단일 실행 Python 봇 구현
- `config/`
  - 기존 봇 환경설정
- `tests/`
  - 기존 전략/리스크/페이퍼 트레이더 테스트
- `frontend/`
  - Next.js 기반 웹 UI 골격
- `api/`
  - FastAPI 기반 인증, bot config, run API 골격
- `worker/`
  - 사용자별 봇 런타임이 들어갈 Python worker 골격
- `shared/`
  - API와 worker가 공유할 도메인 모델/전략 인터페이스
- `docs/`
  - 웹앱 아키텍처 및 마이그레이션 문서
- `legacy/`
  - 기존 단일 봇 코드를 참조 자산으로 유지하기 위한 안내

## 기술 스택 요약

- 기존 엔진
  - Python 3.11
  - asyncio
  - py-clob-client
  - httpx
  - websockets
  - pandas / ta
- 새 웹앱 구조
  - frontend: Next.js 15, React 19, TypeScript
  - api: FastAPI, SQLite 초기 persistence, eth-account, pydantic-settings
  - worker: Python 3.11 runtime skeleton
  - shared: Python shared contracts

## 에이전트 간 역할 분담

- `Codex`
  - 현재 유일한 활성 에이전트
  - 담당 영역: 아키텍처 설계, 문서 정리, API 스캐폴딩, frontend/worker 초기 구조 생성
- 추가 에이전트
  - 아직 없음
  - 합류 시 아래 파일들을 먼저 확인해야 한다:
    - `README.md`
    - `research.md`
    - `plan.md`

## 작업 진행 상태

- 현재 단계: `계획 + 초기 구현 + 문서 정렬`
- 상태 설명:
  - web app 전환 설계 완료
  - `frontend / api / worker / shared` 골격 생성 완료
  - API의 nonce/session/bot persistence 초안 구현 완료
  - 추가 구현은 현재 문서 기준선 정리 후 이어갈 예정

## 참고 파일 안내

- `research.md`
  - 현재 시스템이 실제로 어떻게 동작하는지에 대한 상세 분석
  - legacy Python bot 구조와 새 web app 골격 모두 포함
- `plan.md`
  - 앞으로 어떤 파일을 어떤 방식으로 바꿀지에 대한 구현 계획
  - 단계별 TODO, 트레이드오프, iteration 메모 포함
- `docs/WEBAPP_ARCHITECTURE.md`
  - 목표 아키텍처 개요
- `docs/MIGRATION_PLAN.md`
  - legacy 코드를 새 구조로 옮기는 방향

## 현재 체크포인트

- legacy 봇은 여전히 `src/main.py`로 이해할 수 있다.
- 새 web app 시작점은 `frontend/`, `api/`, `worker/`, `shared/` 이다.
- 다음 구현 전에 `plan.md` 승인과 보완을 먼저 반영해야 한다.

## 업데이트 규칙

이 파일은 온보딩 문서다. 아래 상황이 생기면 즉시 갱신해야 한다.

- 작업 단계가 바뀔 때
- 다른 에이전트가 합류할 때
- 역할 분담이 바뀔 때
- 구현 우선순위가 달라질 때
