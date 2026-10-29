# 쇼츠 편집 툴 명세 v0.2

원본: 노션 `유튜브 영상 자동 편집툴 / 개발 문서` (기능 명세서·API 명세서). 이 파일이 저장소 기준본이다.

## 1. 사용자 흐름

| 화면 | 사용자 행동 | 서버 작업 |
|---|---|---|
| 템플릿 선택 | 연예인 꿀템 선택 (TOP 3·썰 풀기는 준비 중) | - |
| 링크 입력 | 유튜브 URL 입력 | 분석 작업 생성 |
| 진행률 | 대기 (자막 있으면 30초~1분) | 영상 정보 → 자막 → 오디오 → (Whisper) → 제품 구간 추천 |
| 장면 고르기 | 추천 구간 클릭, 핸들 조정, '이 구간으로 만들기' | 쇼츠 작업 생성 |
| 진행률 | 대기 | 구간 다운로드 → 구간 Whisper → 크롭 → 제목·나레이션·TTS → 미리보기 |
| 편집기 | 단어 삭제, 쉼 줄이기, AI 추천 컷, 자막 수정, 제목·나레이션 수정, 스타일 | 편집 상태 저장 → 미리보기 재렌더 |
| 출력 | 출력하기, 다운로드, 업로드 문구 복사, 파트너스 링크 붙여넣기, 평가 | 최종 렌더, 업로드 키트 생성 |

## 2. 작업 상태

| 작업 | 상태 흐름 | 진행률 가중치 |
|---|---|---|
| 분석 | queued → fetching → (transcribing) → analyzing → ready / failed | fetching 0.2 / transcribing 0.5 / analyzing 0.3. 자막 있으면 0.4 / - / 0.6 |
| 쇼츠 | queued → downloading → preparing → editing ⇄ rendering → done / failed | downloading 0.3 / preparing 0.7 |

- transcribing은 유튜브 ko 자막이 없을 때만
- 출력(done) 후 편집하면 editing으로 돌아감
- 동시 진행 작업 최대 2개 (분석+쇼츠 합산). 쇼츠 editing은 사용자 대기라 세지 않음 (queued·downloading·preparing·rendering만)
- 재시도는 실패 단계부터, 최대 3회. 단계 산출물 파일이 있으면 건너뛰는 방식 (파일은 임시 파일 → rename으로 완성본만 남김)

## 3. 파일

| 경로 | 생성 단계 | 내용 |
|---|---|---|
| `data/analyses/{id}/meta.json` | fetching | yt-dlp 영상 정보 일부 |
| `data/analyses/{id}/audio.m4a` | fetching | 오디오 (파형·Whisper·신호) |
| `data/analyses/{id}/transcript.json` | fetching / transcribing | `{source: manual|auto|whisper, sentences: [{id, start_sec, end_sec, text}]}` |
| `data/analyses/{id}/waveform.json` | fetching | 초당 10개 피크 |
| `data/analyses/{id}/mentions.json` | analyzing | LLM 제품 언급 추출 결과 |
| `data/analyses/{id}/signals.json` | analyzing | 후보 구간별 신호값 (학습 피처) |
| `data/analyses/{id}/recommendations.json` | analyzing | 상위 3개 추천 |
| `data/shorts/{id}/section.mp4` | downloading | 선택 구간 ±1초 |
| `data/shorts/{id}/words.json` | preparing | `{source: whisper, words: [{text, start_sec, end_sec}]}` 구간 전체(여유 포함), 원본 기준 초 |
| `data/shorts/{id}/crop.json` | preparing | `{width, height, crop_w, crop_h, y, keyframes: [{t, x}]}` 9:16 고정 크기 창을 가로로만 이동. 0.5초 간격 가장 큰 얼굴 중심, 빈 곳은 직전 얼굴 유지, 이동 평균 5개 |
| `data/shorts/{id}/edit.json` | preparing / 편집 | 편집 상태 (6절) |
| `data/shorts/{id}/narration/*.mp3` | preparing / 편집 | TTS 결과 (`data/tts_cache/` 해시 캐시 링크) |
| `data/shorts/{id}/preview.mp4` | preparing / 편집 | 540×960. 같은 폴더에 `subs.ass`·`render.filter`·`render.log` (렌더 중간 파일) |
| `data/shorts/{id}/final.mp4`, `final.srt`, `thumbnail.jpg` | rendering | 1080×1920 |
| `data/shorts/{id}/publish_kit.json` | 출력 후 | 업로드 키트 |

## 4. DB

| 테이블 | 주요 컬럼 |
|---|---|
| analyses | id, video_id, url, template_id, status, stage, progress_weight_mode, transcript_source, warnings(json), error_code, error_message, retry_count, source(json), created_at, finished_at |
| shorts | id, analysis_id, template_id, status, stage, start_sec, end_sec, section_offset_sec, edit_version, preview_version, preview_status, warnings(json), error_code, error_message, retry_count, created_at, exported_at |
| selection_logs | id, analysis_id(nullable), short_id(nullable), video_id, recommended(json: rank·구간·점수·신호), chosen_start_sec, chosen_end_sec, recommendation_rank, scorer_version, created_at |
| feedback | short_id(unique, nullable), video_id, range(json), signals(json), scorer_version, kept, views, link_clicks, orders, updated_at |

- id 형식: `an_` + 8자, `sh_` + 8자 (base32 소문자)
- 분석·쇼츠 삭제 시 selection_logs·feedback은 남기고 FK만 null

## 5. 제품 구간 추천 (HL-01, HL-02)

### 5.1 처리 순서

1. LLM 1회: 문장별 `{product, brand, category, recommend_strength(0~1), usage(bool)}`. 제목·설명란을 브랜드 보정 힌트로 제공. 확신 없으면 brand null
2. 후보 생성: 같은 제품 언급 문장을 묶음 (제품 없는 문장 1개까지 사이에 허용) → 앞뒤 1문장 문맥 추가
3. 길이 맞춤: 30초 미만이면 뒤 문장 우선으로 확장, 60초 초과면 문장 경계로 분할
4. 신호 계산 (5.2) → 점수 → 겹침 제거 (IoU > 0.3이면 낮은 쪽 제거) → 상위 3개
5. 태그 (5.3)
6. 경계: 문장 시작·끝 기준, 앞뒤 0.2초 여유

### 5.2 신호와 점수 (MVP RulesScorer)

| 신호 | 계산 | 가중치 |
|---|---|---|
| product_specific | 제품+브랜드 1.0 / 제품만 0.6 / 없음 0 | 0.30 |
| recommend_strength | 구간 내 최대 recommend_strength | 0.25 |
| usage | usage=true 문장 비율 ×2, 최대 1 | 0.15 |
| density | 초당 글자 수 / 7, 최대 1 | 0.10 |
| continuity | 1 − (1초 초과 공백 수 / 문장 수), 제품이 2개 이상 섞이면 ×0.5 | 0.10 |
| length_fit | 35~55초 1.0, 30·60초 0.5로 선형 감소 | 0.10 |

- 가중치·임계값은 `config.py`. 신호값은 전부 signals.json에 저장 (2단계 학습 피처)
- 점수 모델 인터페이스: `score(candidates, signals) -> list[float]`. 버전 문자열(`rules-v1`)을 결과와 로그에 남김

### 5.3 이유 태그

| 코드 | 화면 문구 | 조건 |
|---|---|---|
| brand_mention | 소개하는 말 '{브랜드}' | brand 있음 |
| usage_scene | 사용하는 장면 | usage ≥ 0.3 |
| strong_recommend | 강하게 추천해요 | recommend_strength ≥ 0.7 |
| dense_speech | 대사가 촘촘합니다 | density ≥ 0.7 |
| continuous | 끊김 없이 이어집니다 | continuity ≥ 0.8 |

- 구간당 최대 2개, 신호 초과량이 큰 순. brand_mention의 초과량은 product_specific − 0.6

### 5.4 산출물

- `mentions.json`: `{source: llm|keywords, model, mentions: [{sentence_id, product, brand, category, recommend_strength, usage}]}`. 제품 없는 문장은 넣지 않는다. LLM 실패 시 키워드 규칙 + 경고 `llm_fallback`
- `signals.json`: `{scorer_version, candidates: [{id, start_sec, end_sec, product_key, signals, score, selected_rank}]}` (모든 후보)
- `recommendations.json`: `{scorer_version, items: [{rank, start_sec, end_sec, duration_sec, score, signals, tags, tag_labels, products, preview}]}`. 후보가 없으면 빈 목록 + 경고 `no_recommendations`
- 같은 제품 판단: 공백 제거·소문자로 비교 ("립 밤" = "립밤")

## 6. edit.json

```json
{
  "version": 8,
  "title": {"text": "...", "visible": true},
  "lines": [
    {"id": "l1", "kind": "speech", "deleted": false, "text": "...", "display_text": null,
     "words": [{"id": "w1", "text": "...", "raw_text": null, "start_sec": 293.4, "end_sec": 294.1,
                "deleted": false, "trim_gap_after": false, "emphasis": false}]},
    {"id": "n1", "kind": "narration", "text": "...", "anchor_line_id": "l7",
     "audio_path": "narration/n1.mp3", "audio_sec": 2.1, "voice_id": "default"}
  ],
  "style": {"preset_id": "title_pink", "overrides": {}},
  "pending_suggestions": [{"id": "s1", "type": "filler", "word_ids": ["w9"], "reason": "..."}]
}
```

### 초안 만들기 (preparing)
- 순서: 구간 Whisper(단어) → 크롭 → 받아쓰기 교정 → 제목·나레이션(LLM 1회) → TTS → edit.json → 첫 미리보기. 진행률 비중 0.4 / 0.2 / 0.1 / 0.3. 미리보기까지 끝나야 editing
- 문장(line): 선택 구간 안(단어 중간 시각 기준) 단어를 자막 문장 규칙으로 묶음. id `l1…`, 단어 id `w1…`. 대사가 없으면 실패 `no_speech`
- 제목 ≤30자, 나레이션 0~2개·각 ≤40자, anchor는 실제 문장만·문장당 1개. 나레이션은 lines에서 anchor 바로 앞에 둔다
- LLM 실패 시 원본 영상 제목(30자)·나레이션 없음 + 경고 `llm_fallback`. 얼굴 검출 실패 시 가운데 크롭 + 경고 `crop_fallback`
- TTS 캐시 키: sha256(제공자, voice_id, 문장). 쇼츠 폴더로 복사

### 받아쓰기 교정
- Whisper 힌트: 구간에 언급된 제품·브랜드 이름(mentions.json)을 hotwords로 (최대 200자)
- 분석 자막이 수동(manual)이면: 구간과 겹치는 자막 문장을 공백 빼고 글자 단위로 Whisper 단어에 맞춰 글자만 바꾼다 (시간은 Whisper 그대로). 일치율 0.6 미만이면 포기
- 그 외(자동 자막·Whisper·맞추기 실패): LLM 1회, 확실한 오인식(고유명사 등)만 `{word_id, text}`로. 단어 합치기·나누기 금지, 20자 이하. 실패하면 교정 없이 진행
- 바뀐 단어는 `raw_text`에 원래 받아쓰기 결과를 남긴다 (편집기 표시·되돌리기용)

### 렌더 규칙
- 유지 구간: 살아 있는 단어 시작 ~ 바로 다음 단어(지운 단어 포함) 시작, 마지막 단어는 끝까지. `trim_gap_after`면 단어 끝 + 0.15초까지. 지운 단어·문장은 통째로 빠진다
- 출력 길이 5~60초, 벗어나면 편집·출력 거부
- 나레이션: anchor 문장의 출력 시작 시각에 믹싱, 그 동안 원본 음성 20%
- 크롭: crop.json 키프레임 선형 보간
- 자막: 문장 단위, 한 줄 최대 16자·최대 2줄, 강조 단어는 프리셋 강조색
- preview 540×960 veryfast CRF 28 / final 1080×1920 CRF 20 veryfast. 자막 좌표는 1080×1920 기준(ASS PlayRes), 폰트는 `assets/fonts` Pretendard Bold
- 미리보기 완료 시 `preview_status=ready`, `preview_version=edit.version`, SSE `preview_ready {preview_version}`
- 미리보기는 편집 후 1초 디바운스, 진행 중이면 취소 후 재시작

### 편집 연산 (PATCH /edit)

| op | 필드 |
|---|---|
| delete_words / restore_words | word_ids |
| delete_line / restore_line | line_id |
| restore_all | - |
| set_display_text | line_id, text |
| set_word_text | word_id, text(1~20자). 시간은 유지, 처음 바꿀 때 `raw_text`에 원문 보관 |
| split_line | line_id, word_id |
| set_title | text(≤30), visible |
| set_narration / add_narration / delete_narration | line_id, text(≤40), anchor_line_id |
| apply_suggestions | suggestion_ids |
| set_style | preset_id, overrides |

- `base_version` 불일치 409. 전부 검증 후 원자적 적용

## 7. 내부 API (Base `http://127.0.0.1:8000/api/v1`, 인증 없음)

| Method | Path | 요약 | 주요 에러 |
|---|---|---|---|
| POST | /analyses | `{url, template_id}` → 202, 재사용 시 200 | 422 invalid_url·video_unavailable·video_too_long, 429 |
| GET | /analyses | 목록, `status`·`limit`·`cursor` | 422 |
| GET | /analyses/{id} | 상태·진행률·경고·에러 | 404 |
| DELETE | /analyses/{id} | 하위 쇼츠 포함 삭제 | 409, 404 |
| GET | /analyses/{id}/recommendations | 추천 ≤3, tags·tag_labels·products·preview | 409 analysis_not_ready |
| GET | /analyses/{id}/transcript | 문장 목록, `start_sec`·`end_sec` | 409 transcript_not_ready |
| GET | /analyses/{id}/waveform | `{duration_sec, peaks_per_sec, peaks}` | 409 |
| GET | /{analyses\|shorts}/{id}/events | SSE: progress, preview_ready, done, failed | 404 |
| POST | /{analyses\|shorts}/{id}/retry | 실패 단계부터 | 409 invalid_state·retry_limit |
| GET | /templates | 템플릿 목록·available | - |
| GET | /styles | 스타일 프리셋 | - |
| POST | /shorts | `{analysis_id, template_id, start_sec, end_sec, recommendation_rank}` → 202. 15~60초. selection_logs 기록 | 409, 422, 429 |
| GET | /shorts/{id} | 상태·edit_version·preview_version | 404 |
| GET | /shorts/{id}/edit | edit.json + duration_sec + out_start_sec | 409 |
| PATCH | /shorts/{id}/edit | `{base_version, ops}` → `{version, duration_sec, preview_status}` | 409 version_conflict, 422 |
| POST | /shorts/{id}/cut-suggestions | `{type: silence, min_gap_sec}` 또는 `{type: filler}` | 422 |
| POST | /shorts/{id}/export | `{base_version}` → 202 rendering | 409 |
| GET | /shorts/{id}/files/{kind} | preview·video·srt·thumbnail, Range 지원, `?download=1` | 404, 422 |
| GET | /shorts/{id}/publish-kit | 없으면 생성, `?regenerate=1` | 409 |
| PATCH | /shorts/{id}/publish-kit | 문구·partner_url(`https://link.coupang.com/`만) | 422 |
| PUT | /shorts/{id}/feedback | `{kept, views, link_clicks, orders}` | 409, 422 |
| GET | /scorers | 2단계 | - |

- SSE 페이로드: `progress {stage, progress}` · `done {status}` · `failed {error, detail}`. 쇼츠는 초안이 준비되면(editing) `done {status: editing}` 연결 직후 현재 상태를 먼저 보내고, done·failed 후 닫는다. 조용한 구간에는 heartbeat로 현재 상태를 다시 보낸다 (Redis가 없어도 DB 폴링으로 동작)

요청·응답 예시 전문은 노션 API 명세서 각 페이지.

## 8. 외부 연동

| 이름 | 방식 | 호출 위치 | 비고 |
|---|---|---|---|
| 영상 정보 | 비공식 도구 (yt-dlp `extract_info(download=False)`) | 분석 생성 | 10초 타임아웃 |
| 자막 | 비공식 도구 (yt-dlp, ko, json3) | fetching | 수동 우선, 자동은 겹침 제거. 한글 비율 30% 미만 트랙은 건너뜀 (언어 표기 오류) |
| 오디오 | 비공식 도구 (yt-dlp bestaudio) | fetching | 항상 받음 |
| 구간 다운로드 | 비공식 도구 (yt-dlp `--download-sections`, `--force-keyframes-at-cuts`) | 쇼츠 downloading | 1080p 이하 |
| 제품 언급 추출 | 공식 API (Claude) | analyzing | 분석당 1회, JSON 강제, 실패 시 키워드 규칙 |
| 문구 생성 | 공식 API (Claude) | 쇼츠 preparing, 업로드 키트 | 프롬프트 파일 관리 |
| TTS | 미정 (인터페이스) | preparing, 나레이션 수정 | FakeTTS 먼저, 해시 캐시 |
| Whisper | 로컬 모델 (faster-whisper) | transcribing, 쇼츠 preparing | `WHISPER_MODEL`, `WHISPER_DEVICE`, vad_filter |
| 얼굴 검출 | 로컬 모델 (MediaPipe) | preparing | 0.5초 간격 |
| 쿠팡 파트너스 | 공식 API | 2단계 | 최종 승인 후 |
| 히트맵 | 비공식 도구 | 2단계 학습 | 보조 라벨 |

## 9. 환경변수

| 이름 | 기본값 | 설명 |
|---|---|---|
| ANTHROPIC_API_KEY | - | 필수 |
| LLM_MODEL | claude-haiku-5-5 | |
| TTS_PROVIDER | fake | fake / openai / elevenlabs / local |
| WHISPER_MODEL | large-v3 | GPU 없으면 small |
| WHISPER_DEVICE | cuda | cuda / cpu |
| REDIS_URL | redis://localhost:6379/0 | |
| DATA_DIR | ./data | |
| SCORER | rules-v1 | |
| MAX_ACTIVE_JOBS | 2 | |
| MAX_SOURCE_SEC | 7200 | |

## 10. 요구사항 ID

| ID | 내용 | 단계 |
|---|---|---|
| IN-01 | 유튜브 링크 입력·검증·수집 | MVP |
| JOB-01 | 작업 상태·진행률·재시도·삭제 | MVP |
| STT-01 | 자막 수집, 없으면 Whisper | MVP |
| HL-01 | 제품 구간 추천·이유 태그 | MVP |
| HL-02 | 문장 경계 맞추기 | MVP |
| HL-03 | 점수 모델 학습·비교 | 2단계 |
| TPL-01 | 템플릿 | MVP (celeb_item) |
| GEN-01 | 쇼츠 초안·제목·나레이션 | MVP |
| RND-01 | 9:16 크롭 | MVP |
| RND-02 | 자막 렌더·출력 | MVP |
| EDIT-01 | 장면 고르기 화면 | MVP |
| EDIT-02 | 대본 컷 편집·미리보기 | MVP |
| STY-01 | 스타일 프리셋 | MVP |
| LINK-01 | 쿠팡 링크 (MVP 검색 링크, 2단계 API) | MVP / 2단계 |
| PUB-01 | 업로드 키트 (MVP), 멀티 업로드 (2단계) | MVP / 2단계 |
| FB-01 | 선택 로그·평가·성과 | MVP |
| DATA-01 | 학습 데이터 수집 | 2단계 |
