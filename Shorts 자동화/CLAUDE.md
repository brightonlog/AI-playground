# CLAUDE.md

유튜브 링크 → 제품 소개 구간 추천 → 쇼츠 초안 → 대본 편집 → 출력까지 하는 개인용 쇼츠 편집 툴.
상세 명세는 `docs/spec.md`. 명세와 코드가 다르면 명세를 먼저 고치고 코드를 바꾼다.

## 작업 방식 (모든 코드 작업에 적용)

1. 계획을 세운다
2. 계획을 검토한다
3. 검토가 맞는지 다시 검토한다
4. 계획이 과도하지 않은지 검토한다
5. 구현한다
6. 구현이 목적에 맞는지 검토한다
7. 잠재 버그·크리티컬 이슈·보안 문제를 검토한다
8. 개선한 내용에 문제가 없는지 검토한다
9. 너무 큰 함수·파일은 적절한 크기로 나눈다
10. 기존 코드와 통합·재사용할 부분이 있는지 검토한다
11. 사이드 이펙트를 확인한다
12. 전체 변경 사항을 다시 검토한다
13. 구현 중 불필요해진 코드를 정리한다
14. 코드 품질이 충분한지 검토한다
15. 사용자 흐름에 문제가 없는지 확인한다
16. 배포해도 될 품질인지 다시 검토한다
17. 커밋하고 PR을 작성한다

- 작업 시작 전 계획을 짧게 보여 주고 시작한다
- 한 PR = 한 마일스톤 하위 작업. 여러 마일스톤을 한 PR에 섞지 않는다
- 커밋 메시지: `feat(analysis): 자막 수집 추가` 형식 (Conventional Commits, 본문 한국어)

## 기술 스택

| 영역 | 선택 |
|---|---|
| 백엔드 | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| DB | SQLite (`data/app.db`) |
| 작업 큐 | Celery + Redis (진행률·SSE Pub/Sub도 Redis) |
| 영상 소스 | yt-dlp (Python 라이브러리로 호출, CLI 아님) |
| 받아쓰기 | faster-whisper |
| 얼굴 검출 | MediaPipe Tasks FaceDetector |
| 렌더 | ffmpeg (시스템 설치), ASS 자막 |
| LLM | anthropic SDK, 모델은 `LLM_MODEL` 환경변수 (기본 `claude-haiku-5-5`) |
| TTS | `TTSProvider` 인터페이스. 제공자 미정, `FakeTTS`로 먼저 완성 |
| 프론트 | Next.js (App Router) + TypeScript, Tailwind, wavesurfer.js, YouTube IFrame API |
| API 타입 | FastAPI OpenAPI → `openapi-typescript`로 프론트 타입 생성 |
| 패키지 | 백엔드 `uv`, 프론트 `pnpm` |
| 품질 | ruff, mypy(strict 아님), pytest / eslint, tsc |

## 폴더 구조

```
backend/
  app/
    api/          # 라우터: analyses, shorts, edit, catalog, events, files
    core/         # config, errors, ids, logging
    db/           # models, session, migrations
    schemas/      # Pydantic 요청·응답, edit.json 스키마
    services/     # 비즈니스 로직 (라우터는 얇게)
    workers/      # Celery 태스크: analysis_tasks, short_tasks, render_tasks, pipeline
    sources/      # youtube.py (yt-dlp 래핑)
    transcript/   # captions.py, whisper.py, sentences.py
    recommend/    # extract, candidates, signals, scorer, tags
    generate/     # copywriter, tts, templates, prompts/*.md
    media/        # crop, render, subtitles, waveform, styles
    llm/          # client.py
    storage/      # local.py (data/ 경로 관리)
  tests/
    fixtures/     # json3 자막, 짧은 테스트 영상(5초), LLM 응답 샘플
frontend/
assets/fonts/     # OFL 한글 폰트 (Pretendard)
training/         # 2단계 학습 스크립트
data/             # 런타임 산출물. git 제외
docs/spec.md
docker-compose.yml  # redis
```

## 코딩 규칙

- 라우터에는 검증과 서비스 호출만. 로직은 `services/`
- 외부 호출(yt-dlp, Claude, TTS, Whisper, MediaPipe)은 전부 인터페이스 뒤에 둔다. 테스트는 Fake 구현으로 돌린다
- 테스트에서 네트워크를 쓰지 않는다. 외부 응답은 `tests/fixtures/`에 저장해 재생한다
- 비밀값은 `.env`에서만 읽는다. 코드·로그·에러 메시지에 키를 남기지 않는다. `.env.example` 유지
- 점수 가중치·임계값·길이 제한은 `app/core/config.py` 한 곳에 둔다. 코드 중간에 숫자를 박지 않는다
- 파일 경로는 DB 값과 `storage/local.py`로만 만든다. 요청값을 경로에 직접 붙이지 않는다
- 시간은 전부 원본 영상 기준 초(float, 소수 1~2자리). 편집 후 시각은 계산값으로만 쓴다
- 에러 응답은 `{"error": "<code>", "detail": "<사람이 읽는 설명>"}`
- 함수 50줄, 파일 300줄을 넘기면 나눌지 검토한다
- 프롬프트는 `generate/prompts/*.md` 파일로 관리. 코드에 긴 문자열을 넣지 않는다

## 제약

- 소스 영상 범위: 유튜브 링크 아무거나 (사용자 결정, 개인 사용 목적)
- 로그인·연령 제한·DRM을 우회하는 코드(쿠키 주입 등)는 작성하지 않는다. 해당 영상은 거부한다
- 업로드 키트의 대가성 문구는 수정·삭제할 수 없게 한다
- yt-dlp는 비공식 도구라 자주 깨진다. 버전을 고정하지 말고, 깨지면 업데이트를 먼저 시도한다

## 마일스톤

| 단계 | 범위 | 완료 기준 |
|---|---|---|
| M0 뼈대 | FastAPI, SQLite, Alembic, Redis, Celery, 설정, 에러 형식, `/health` | `docker compose up` + 서버 + 워커 기동, pytest 통과 |
| M1 분석 수집 | 분석 시작·조회·목록·삭제·재시도, 영상 정보, 자막(json3→문장), 오디오, Whisper 대체, 파형, SSE | 자막 있는 영상·없는 영상 각각 ready까지, 대사·파형 API 응답 |
| M2 구간 추천 | LLM 제품 추출, 후보 생성, 신호, 규칙 점수, 태그, 추천 API, signals.json | 테스트 영상 3개에서 추천 3개 이하·비겹침·30~60초 |
| M3 프론트 1 | 템플릿 선택, 링크 입력, 진행률, 장면 고르기(플레이어·추천·파형 타임라인·대사·문장 스냅) | 추천 클릭 → 구간 이동 → 만들기 버튼까지 동작 |
| M4 쇼츠 초안 | 쇼츠 생성, 구간 다운로드, 구간 Whisper, 크롭, 제목·나레이션, FakeTTS, edit.json, 미리보기 렌더 | editing 상태 + preview.mp4 재생 |
| M5 편집기 | 편집 조회·수정(ops), 컷 추천, 스타일, 미리보기 자동 갱신, 프론트 편집기 | 단어 삭제 → 미리보기 반영 |
| M6 출력 | 최종 렌더, 파일 받기, 업로드 키트 조회·수정, 쇼츠 평가 | 1080×1920 mp4 + srt + 업로드 문구 복사 |
| 2단계 | 실제 TTS, 쿠팡 API, 학습 데이터·모델, TOP 3·썰 풀기, 멀티 업로드 | 별도 계획 |

## 명령어

```
cp .env.example .env
docker compose up -d redis
cd backend && uv sync --extra cuda   # GPU Whisper (Windows CUDA DLL 포함). GPU 없으면 --extra 빼고 WHISPER_DEVICE=cpu, WHISPER_MODEL=small
cd backend && uv run alembic upgrade head
cd backend && uv run uvicorn app.main:app --reload
cd backend && uv run celery -A app.workers.celery_app worker -l info -P solo   # Windows는 -P solo 필수
cd backend && uv run pytest
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app
cd frontend && pnpm dev
```

- 헬스 체크: `GET http://127.0.0.1:8000/api/v1/health` → `{"status":"ok","db":true,"redis":true}` (Redis 끊기면 `degraded`)
- `.env`는 저장소 루트에 둔다. `DATA_DIR` 기본값은 `<루트>/data`
