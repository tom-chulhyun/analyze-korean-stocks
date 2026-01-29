# Handoff Document - 한국 주식 분석 리포트 생성기

## 프로젝트 개요
한국 주식의 거래대금, 등락률, 기술적 지표(RSI, TRIX, MACD), 네이버 뉴스, DART 공시 자료를 기반으로 PDF 리포트를 생성하고, 카카오톡으로 자동 전송하는 Python CLI 애플리케이션

## 현재 상태: 구현 완료

### 완료된 기능
| 기능 | 상태 | 라이브러리 |
|------|------|-----------|
| 주가 데이터 수집 | ✅ 완료 | pykrx |
| 기술적 지표 (RSI, TRIX, MACD) | ✅ 완료 | pandas-ta |
| 매매 시그널 생성 | ✅ 완료 | 자체 구현 |
| DART 재무제표 | ✅ 완료 | OpenDartReader |
| 네이버 뉴스 수집 | ✅ 완료 | 네이버 검색 API |
| AI 분석 (요약, 감성, 의견) | ✅ 완료 | OpenAI |
| PDF 리포트 생성 | ✅ 완료 | Jinja2 + WeasyPrint |
| CLI 인터페이스 | ✅ 완료 | typer + rich |
| 카카오톡 전송 | ✅ 완료 | REST API |
| Google Drive 업로드 | ✅ 완료 | Google API |

### 테스트 현황
- 단위 테스트: 14개 통과 (collectors, indicators)
- 통합 테스트: 마커로 분리됨 (`@pytest.mark.integration`)
- PDF 생성 테스트: 삼성전자(005930) 1개월/3개월 리포트 성공

---

## 프로젝트 구조

```
analyze-korean-stocks/
├── pyproject.toml          # 의존성 정의 (Python 3.12+)
├── .env                    # 환경변수 (API 키)
├── .env.example            # 환경변수 템플릿
├── CLAUDE.md               # Claude Code 프로젝트 지침
├── README.md               # 사용자 문서
├── src/stock_analyzer/
│   ├── main.py             # CLI 진입점
│   ├── config.py           # Pydantic Settings
│   ├── collectors/
│   │   ├── stock_price.py  # pykrx 주가 수집
│   │   ├── dart.py         # DART 재무제표
│   │   └── news.py         # 네이버 검색 API
│   ├── indicators/
│   │   └── technical.py    # RSI, TRIX, MACD
│   ├── analyzers/
│   │   ├── stock_analyzer.py # 종합 분석
│   │   └── ai_analyzer.py    # OpenAI 분석
│   ├── reports/
│   │   ├── generator.py    # PDF 생성
│   │   └── templates/
│   │       └── report.html # Jinja2 템플릿
│   ├── notifiers/
│   │   ├── kakao.py        # 카카오톡 전송
│   │   └── uploader.py     # Google Drive
│   └── models/
│       └── schemas.py      # Pydantic 모델
├── tests/                  # 테스트 코드
├── docs/                   # 문서
│   ├── SPEC.md             # 기술 스펙
│   └── API_SETUP.md        # API 설정 가이드
└── output/                 # 생성된 리포트
```

---

## 환경 설정

### 시스템 요구사항
- Python 3.12+
- macOS: WeasyPrint 의존성 필요

### WeasyPrint 시스템 의존성 (macOS)
```bash
brew install pango gdk-pixbuf cairo gobject-introspection
```

### 환경변수 (~/.zshrc에 추가됨)
```bash
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
```

### .env 파일 설정
```env
# DART API (재무제표)
DART_API_KEY=your_key

# OpenAI (AI 분석)
OPENAI_API_KEY=sk-...

# 네이버 검색 API (뉴스)
NAVER_CLIENT_ID=your_id
NAVER_CLIENT_SECRET=your_secret

# 카카오톡 (메시지 전송)
KAKAO_REST_API_KEY=your_key
KAKAO_REDIRECT_URI=http://localhost:8080/callback

# Google Drive (파일 업로드)
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

---

## 실행 방법

### 의존성 설치
```bash
uv sync --all-extras
```

### CLI 실행
```bash
# 기본 (1주 + 1개월 리포트 2개)
uv run stock-report 005930

# 커스텀 기간
uv run stock-report 005930 --preset 3m     # 3개월
uv run stock-report 005930 --period 90     # 90일
uv run stock-report 005930 --start 2024-01-01 --end 2024-12-31

# 옵션
uv run stock-report 005930 --no-ai         # AI 분석 제외
uv run stock-report 005930 --kakao         # 카카오톡 전송
uv run stock-report 005930 -o ./my-reports # 출력 디렉토리

# 여러 종목
uv run stock-report 005930 000660 035720
```

### 테스트 실행
```bash
# 단위 테스트만
uv run pytest tests/ -v -m "not integration"

# 전체 테스트
uv run pytest tests/ -v
```

---

## 알려진 이슈 및 제한사항

### 1. pykrx get_market_ticker_list 문제
- **증상**: `get_market_ticker_list()`가 빈 리스트 반환
- **원인**: pykrx의 영업일 계산 로직 문제
- **해결**: `get_market_ticker_name()` 직접 호출 + OHLCV 조회로 fallback
- **위치**: `collectors/stock_price.py` `_get_stock_name()`, `_get_market()`

### 2. DART 재무제표 조회 실패
- **증상**: "조회된 데이타가 없습니다" 메시지
- **원인**: 미래 연도(2026년) 데이터 없음 또는 API 제한
- **영향**: 재무제표 섹션이 비어있음 (graceful degradation)

### 3. matplotlib 한글 폰트
- **증상**: "Font family not found" 경고
- **해결**: `plt.rcParams["font.family"] = "AppleGothic"` (macOS)
- **위치**: `reports/generator.py`

### 4. WeasyPrint 라이브러리 로딩
- **증상**: `cannot load library 'libgobject-2.0-0'`
- **해결**: `DYLD_LIBRARY_PATH="/opt/homebrew/lib"` 환경변수 설정
- **상태**: `~/.zshrc`에 추가됨

### 5. pkg_resources 경고
- **증상**: pykrx import 시 deprecation warning
- **원인**: pykrx가 pkg_resources 사용 (Python 3.13에서 deprecated)
- **영향**: 기능에는 문제 없음, 경고 메시지만 출력

---

## Graceful Degradation

API 키가 없거나 API 호출 실패 시 해당 기능만 비활성화:

| 조건 | 동작 |
|------|------|
| DART API 키 없음 | 재무제표 섹션 제외 |
| OpenAI API 키 없음 | AI 분석 섹션 제외 |
| 네이버 API 키 없음 | 뉴스 섹션 제외 |
| 카카오/구글 키 없음 | 로컬 PDF만 생성 |

---

## 데이터 모델 (Pydantic)

### 주요 모델
- `StockInfo`: 종목 기본 정보 (code, name, market)
- `PriceData`: 일별 가격 데이터 (OHLCV, 거래대금, 등락률)
- `TechnicalIndicators`: 기술적 지표 (RSI, TRIX, MACD)
- `Signal`: 매매 시그널 (BUY/SELL/HOLD, 강도 1-5)
- `FinancialData`: 재무 데이터 (매출, 영업이익, 순이익)
- `NewsArticle`: 뉴스 기사 (제목, 링크, 언론사, 발행일)
- `AIAnalysis`: AI 분석 결과 (요약, 감성, 의견)
- `StockReport`: 종합 리포트 (모든 데이터 포함)

---

## 기술적 지표 시그널 로직

| 지표 | 매수 조건 | 매도 조건 |
|------|----------|----------|
| RSI (14) | < 30 (과매도) | > 70 (과매수) |
| TRIX (15,9) | 시그널 상향 돌파 | 시그널 하향 돌파 |
| MACD (12,26,9) | 시그널 상향 돌파 | 시그널 하향 돌파 |

---

## 향후 개선 사항

1. **테스트 커버리지 확대**
   - reports, analyzers, notifiers 테스트 추가
   - 모킹을 통한 API 호출 테스트

2. **에러 핸들링 강화**
   - 네트워크 오류 재시도 로직
   - 더 상세한 에러 메시지

3. **기능 추가**
   - 이메일 전송 옵션
   - 스케줄러 (cron) 연동
   - 웹 대시보드

4. **성능 최적화**
   - 병렬 데이터 수집
   - 캐싱 레이어

---

## 관련 문서

- `CLAUDE.md` - Claude Code 프로젝트 지침
- `docs/SPEC.md` - 상세 기술 스펙
- `docs/API_SETUP.md` - API 키 발급 가이드
- `README.md` - 사용자 가이드

---

## 최근 변경 이력

### 2026-01-29
- 프로젝트 초기 구현 완료
- pykrx 종목 조회 문제 수정 (OHLCV fallback)
- 네이버 뉴스 크롤링 → 검색 API로 변경
- matplotlib 한글 폰트 설정
- WeasyPrint 시스템 의존성 설치
- PDF 리포트 생성 테스트 성공
