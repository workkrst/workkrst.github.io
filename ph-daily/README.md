# PH 데일리 (Product Hunt Daily)

Product Hunt 업보트 Top 5를 매일 자동 수집·번역·발행하는 정적 리포트.

- 목록: https://workkrst.github.io/ph-daily/
- 일일: `/ph-daily/YYYY-MM-DD/`

## 파이프라인 (크론 2단, KST)

### 1) 수집 — 매일 12:00 (무음)
1. `_build/fetch_ph.py home <out.md>` — PH 홈에서 업보트 Top5 slug 선정
2. 제품별 `_build/fetch_ph.py slug {S} <out.md>` — Apify web-fetch로 제품 페이지 원문 저장
   → `_pending/{D}/raw/{S}.md` (403·차단 대응은 Apify가 처리, 3,000자 미만이면 `/posts/`→`/products/` 폴백)
3. LLM이 선정·번역·요약 → `_pending/{D}/{A,B,C}.json`
   - 제품 정보·댓글 번역·comment_summary 포함. 필수 필드는 `publish.py`의 `REQ` 참조
4. `_build/fetch_disquiet.py <out.json>` — 디스콰이엇 신규 수집 (아래 섹션 참조)
   - **부가 작업**: 실패해도 전체 실패 아님 — 조용히 무시하고 당일 디스콰이엇 섹션만 누락

### 2) 발행 — 매일 12:30 (브리핑)
```bash
python3 _build/publish.py merge {D}
python3 _build/publish.py publish {D} --meta /tmp/ph-meta-{D}.json
```
- `merge`: `_pending/{D}/*.json` → `{D}/data.json` 병합. 이때 `extract_website()`가 website 필드 자동 추출(아래 참조)
- `publish`: meta(summary·notable·disquiet) 반영 → `build_report.py`(일일 페이지) → `list_gen.py`(목록) → git push(`pull --rebase --autostash` 내장) → URL 200 확인 → **디스콰이엇 레지스트리 커밋**

## 디스콰이엇 섹션 (2026-10-01 추가)

일일 페이지 PH 섹션 아래에 가로선으로 구분돼 "🇰🇷 디스콰이엇 신규 프로덕트"가 카드로 표시된다. PH Top5 큐레이션과 달리 신규 등록분 전체를 간략 카드(제품명·태그라인·AI 한줄 코멘트·업보트·디스콰이엇 링크)로 나열한다.

- **데이터 흐름**: `fetch_disquiet.py`가 `disquiet.io/products?page=1..2`를 직접 GET(서버사이드 렌더링이라 Apify 불필요, 무료) → "인기 프로덕트" 사이드바·AD 제외 후 메인 리스트 20개/페이지 파싱 → **레지스트리 diff로 오늘 신규만** `_pending/{D}/disquiet.json` 저장
- **중복 관리**: `_pending/disquiet_seen.json`에 본 slug 누적. 갱신본은 `<out.json>.registry`에 임시 저장되고 **URL 200 확인 후에야** 정식 레지스트리로 교체(atomic) — 발행 실패 시 다음 날 diff에 다시 잡혀 유실 없음
- **코멘트**: 발행 크론의 agy 브리프가 disquiet.json을 읽어 제품당 한국어 한줄 코멘트 작성 → meta JSON의 `disquiet` 키로 publish에 전달
- **UI**: `data.json`에 `disquiet` 키가 없거나 빈 배열이면 섹션 자체가 렌더링되지 않음(자동 숨김). 카드 전체 클릭 = 디스콰이엇 페이지 새 탭
- **초기 시딩**: `fetch_disquiet.py <out.json> --init` — 첫 실행 시 레지스트리만 채우고 미출력. `--keep K`로 페이지1 앞 K개는 신규로 남길 수 있음

## 링크 기능 (2026-09-30 추가)

- **`website` 필드**: merge 단계에서 `_pending/{D}/raw/{S}.md` 원문의 `[Visit website](URL)` 마크다운에서 제품 원본 사이트 URL을 자동 추출. `ref=producthunt` 파라미터는 제거, 그 외 utm은 유지. **raw md가 없으면 필드 자체가 없고 → 관련 버튼은 자동 숨김**
- **UI 노출 위치** (`build_report.py` 템플릿):
  - 카드 하단: `🌐 웹사이트`(제품 원본 사이트) / `💬 PH에서 보기`(producthunt.com 제품 페이지 — 댓글 원문 열람) 필 버튼. 버튼 클릭은 모달 열림과 분리(stopPropagation)
  - 상세 모달 헤더: `🌐 웹사이트`(채움 스타일) + `💬 PH에서 보기`(외곽선 스타일). 모바일 좁은 화면 대응 flex-wrap
- `launch_url_used`(PH 페이지 URL)는 전 제품 필수 필드라 💬 버튼은 항상 존재. `website`는 raw md 기반이라 있는 경우만

## 과거 회차 소급(백필) 절차

템플릿에 새 필드/기능을 추가해 과거 회차에도 적용하려면:

1. `_pending/{D}/raw/{S}.md`가 있는 회차(2026-09-23~) → 로컬 원본에서 즉시 추출 가능
2. raw가 없는 회차 → `fetch_ph.py slug {S} _pending/{D}/raw/{S}.md`로 재수집(병렬 4 권장) 후 추출
3. `data.json` 갱신 → `build_report.py {D}` 전 회차 재빌드 → `list_gen.py` → push
4. 재수집해도 추출 안 되는 케이스 존재(예: PH 페이지 자체가 무관한 placeholder 제품) — 버튼 자동 숨김이 정상 동작이므로 방치

2026-09-30 실적: 14회차 70개 제품 중 69개 소급 성공 (weave 1개 제외).

디스콰이엇 섹션은 2026-10-01부터라 과거 회차 소급 대상 아님.

## 파일 구조

```
ph-daily/
├── index.html            # 목록페이지 (list_gen.py가 list-data.js 생성, 페이지 자체는 수동 관리)
├── list-data.js          # 목록 데이터 (빌드 산출물)
├── YYYY-MM-DD/
│   ├── data.json         # 단일 소스(source of truth) — 데이터 수정은 여기만
│   └── index.html        # 빌드 산출물 — 직접 수정 금지 (build_report.py가 재생성)
├── _build/
│   ├── fetch_ph.py       # Apify web-fetch 수집기 (home/slug 모드)
│   ├── fetch_disquiet.py # 디스콰이엇 수집기 (직접 GET + 레지스트리 diff)
│   ├── publish.py        # merge/publish 진입점 + extract_website() + 레지스트리 커밋
│   ├── build_report.py   # 일일 index.html 생성기 (템플릿 내장, 디스콰이엇 섹션 포함)
│   └── list_gen.py       # 목록 데이터 생성기
└── _pending/{D}/         # 수집 원본 (gitignore — 미게시)
    ├── raw/*.md          # PH 페이지 원문 (website 추출 재료)
    ├── {A,B,C}.json      # 번역·요약 산출물
    └── disquiet.json     # 디스콰이엇 오늘 신규 (+ .registry 임시 갱신본)

`_pending/disquiet_seen.json` — 디스콰이엇 중복 필터 레지스트리 (gitignore)
```

## 주의사항

- 일일 `index.html`은 반드시 `build_report.py`로 재생성 — 수작업 수정 금지
- 템플릿 수정 후에는 위 소급 절차로 전 회차 재빌드 권장
- `publish.py` 종료코드: 0 성공 / 2 수집없음 / 3 데이터손상 / 4 빌드실패 / 5 push실패 / 6 URL확인실패
- `_pending/`은 gitignore라 미게시 — raw md 백필 재료이므로 임의 삭제 금지
