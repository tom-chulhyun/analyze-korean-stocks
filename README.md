# 한국 주식 분석 리포트 생성기

한국 주식의 거래대금, 등락률, 기술적 지표(RSI, TRIX, MACD), 네이버 뉴스, DART 공시 자료를 기반으로 PDF 리포트를 생성하고, 카카오톡으로 자동 전송하는 Python CLI 애플리케이션입니다.

## 주요 기능

- **주가 데이터 분석**: pykrx를 통한 OHLCV, 거래대금, 등락률 조회
- **기술적 지표**: RSI (14일), TRIX (15, 9), MACD (12, 26, 9) 계산 및 시그널 생성
- **재무제표**: DART API를 통한 재무제표 조회 (현재 연도 + 전년도 비교)
- **뉴스 분석**: 네이버 뉴스 크롤링 (최근 6개월, 중복 제거 후 10건)
- **AI 분석**: OpenAI를 통한 뉴스 요약, 감성 분석, 종합 의견 생성
- **PDF 리포트**: 차트 포함 종합 분석 리포트 생성
- **카카오톡 전송**: Google Drive 업로드 후 카카오톡 나에게 보내기

## 설치

### 요구사항
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (권장) 또는 pip

### 설치 방법

```bash
# uv 사용 (권장)
uv sync

# 또는 pip 사용
pip install -e .
```

### WeasyPrint 의존성 (macOS)

PDF 생성을 위해 WeasyPrint의 시스템 의존성이 필요합니다:

```bash
# macOS
brew install pango gdk-pixbuf libffi

# Ubuntu/Debian
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```

## 환경 설정

`.env.example`을 `.env`로 복사하고 API 키를 설정합니다:

```bash
cp .env.example .env
```

### 필수 설정
- `DART_API_KEY`: [DART 오픈API](https://opendart.fss.or.kr/)에서 발급

### 선택 설정
- `OPENAI_API_KEY`: AI 분석 기능 사용 시 ([OpenAI](https://platform.openai.com/))
- `KAKAO_REST_API_KEY`: 카카오톡 전송 시 ([카카오 디벨로퍼스](https://developers.kakao.com/))
- `GOOGLE_CREDENTIALS_PATH`: Google Drive 업로드 시 ([Google Cloud Console](https://console.cloud.google.com/))

자세한 API 설정 가이드는 [docs/API_SETUP.md](docs/API_SETUP.md)를 참고하세요.

## 사용법

### 기본 사용

```bash
# 기본 실행 (1주 + 1개월 리포트 2개 생성)
uv run stock-report 005930

# 커스텀 기간 지정
uv run stock-report 005930 --period 90           # 최근 90일
uv run stock-report 005930 --preset 3m           # 3개월
uv run stock-report 005930 --start 2024-01-01 --end 2024-12-31  # 특정 기간

# 카카오톡으로 전송
uv run stock-report 005930 --kakao

# 여러 종목
uv run stock-report 005930 000660 035720

# AI 분석 제외
uv run stock-report 005930 --no-ai

# 출력 디렉토리 지정
uv run stock-report 005930 --output ./my-reports
```

### 기간 옵션

| 옵션 | 동작 |
|------|------|
| (없음) | 1주 + 1개월 리포트 2개 생성 |
| `--period N` | 최근 N일 리포트 1개 |
| `--start/--end` | 지정 기간 리포트 1개 |
| `--preset 1w/1m/3m/6m/1y` | 해당 기간 리포트 1개 |

## 리포트 내용

생성되는 PDF 리포트에는 다음 정보가 포함됩니다:

1. **종목 요약**: 현재가, 등락률, 거래대금
2. **주가 차트**: 종가 추이 및 거래량
3. **기술적 지표**: RSI, TRIX, MACD 차트 및 현재 값
4. **매매 시그널**: 각 지표별 BUY/SELL/HOLD 시그널
5. **재무 정보**: 매출액, 영업이익, 당기순이익 (YoY 비교)
6. **AI 분석** (선택): 뉴스 요약, 감성 분석, 종합 의견
7. **최근 뉴스**: 최근 6개월 내 주요 뉴스 5건

## 프로젝트 구조

```
analyze-korean-stocks/
├── src/stock_analyzer/
│   ├── main.py              # CLI 진입점
│   ├── config.py            # 환경 설정
│   ├── collectors/          # 데이터 수집
│   │   ├── stock_price.py   # 주가 (pykrx)
│   │   ├── dart.py          # DART 공시
│   │   └── news.py          # 네이버 뉴스
│   ├── indicators/
│   │   └── technical.py     # RSI, TRIX, MACD
│   ├── analyzers/
│   │   ├── stock_analyzer.py # 종합 분석
│   │   └── ai_analyzer.py    # AI 분석
│   ├── reports/
│   │   ├── generator.py     # PDF 생성
│   │   └── templates/       # HTML 템플릿
│   ├── notifiers/
│   │   ├── kakao.py         # 카카오톡
│   │   └── uploader.py      # Google Drive
│   └── models/
│       └── schemas.py       # 데이터 모델
├── tests/                   # 테스트
├── docs/                    # 문서
└── output/                  # 생성된 리포트
```

## 개발

### 테스트 실행

```bash
# 단위 테스트만
uv run pytest tests/ -v -m "not integration"

# 전체 테스트 (API 키 필요)
uv run pytest tests/ -v

# 커버리지
uv run pytest tests/ --cov=src/stock_analyzer
```

### 타입 체크

```bash
uv run mypy src/
```

### 린팅

```bash
uv run ruff check src/
uv run ruff format src/
```

## 면책조항

이 도구로 생성된 리포트는 정보 제공 목적으로만 작성되며, 투자 권유나 조언이 아닙니다. 모든 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.

## 라이선스

MIT License
