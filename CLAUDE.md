# Claude Code Project Instructions

## Project Overview
한국 주식 분석 리포트 생성 CLI 애플리케이션 - 거래대금, 등락률, 기술적 지표(RSI, TRIX, MACD), 네이버 뉴스, DART 공시 자료를 기반으로 PDF 리포트를 생성하고 카카오톡으로 전송

## Tech Stack
- **Python 3.11+**
- **Data**: pykrx (주가), OpenDartReader (공시), pandas-ta (기술지표)
- **Scraping**: requests + BeautifulSoup4 (네이버 뉴스)
- **PDF**: Jinja2 + WeasyPrint
- **Charts**: matplotlib
- **CLI**: typer + rich
- **Config**: pydantic-settings + python-dotenv
- **AI**: openai (뉴스 요약, 감성 분석)
- **Notifications**: 카카오톡 REST API, GitHub (리포트 저장)

## Project Structure
```
src/stock_analyzer/
├── main.py              # CLI 진입점 (typer)
├── config.py            # 환경설정 (Pydantic Settings)
├── collectors/          # 데이터 수집
│   ├── stock_price.py   # pykrx 주가/거래대금
│   ├── dart.py          # DART 재무제표
│   └── news.py          # 네이버 뉴스 (최근 6개월, 10건)
├── indicators/
│   └── technical.py     # RSI, TRIX, MACD
├── analyzers/
│   ├── stock_analyzer.py # 종합 분석
│   └── ai_analyzer.py    # OpenAI 기반 분석
├── reports/
│   ├── generator.py     # PDF 생성
│   └── templates/       # HTML/CSS 템플릿
├── notifiers/
│   ├── kakao.py         # 카카오톡 전송
│   └── github_uploader.py  # GitHub 리포트 업로드
└── models/
    └── schemas.py       # Pydantic 모델
```

## Commands
```bash
# Install dependencies
uv sync

# Run CLI (자동 종목 선정)
uv run stock-report                           # 거래대금 상위 10개 자동 분석
uv run stock-report --top 5                   # 상위 5개 종목
uv run stock-report --market KOSDAQ           # KOSDAQ만

# Run CLI (수동 종목 지정)
uv run stock-report 005930 000660             # 지정 종목 분석
uv run stock-report 005930 --period 90        # 90일
uv run stock-report --kakao                   # 자동 선정 + 카카오톡 전송

# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy src/
```

## Key Implementation Details

### Data Collection Periods
- **뉴스**: 최근 6개월, 중복 제거 후 10건
- **재무제표**: 현재 연도 + 전년도 (YoY 비교)
- **주가**: 사용자 지정 기간 (기본 1주/1개월)

### Technical Indicators
- RSI (14일) - 과매수(>70), 과매도(<30)
- TRIX (15일, 시그널 9일) - 0선 돌파, 시그널 교차
- MACD (12, 26, 9) - 시그널 교차, 0선 돌파

### CLI Options
| Option | Behavior |
|--------|----------|
| (none) | 거래대금 상위 10개 종목, 30일 리포트 |
| `--top N` | 상위 N개 종목 자동 선정 |
| `--market KOSPI/KOSDAQ/ALL` | 시장 선택 |
| `--period N` | 최근 N일 리포트 |
| `--preset 1w/1m/3m/6m/1y` | 기간 프리셋 |
| `--no-ai` | AI 분석 제외 |

## Environment Variables
- `DART_API_KEY` - DART API 키
- `OPENAI_API_KEY` - OpenAI API 키
- `NAVER_CLIENT_ID` - 네이버 검색 API Client ID
- `NAVER_CLIENT_SECRET` - 네이버 검색 API Client Secret
- `KAKAO_REST_API_KEY` - 카카오 REST API 키
- `KAKAO_REDIRECT_URI` - OAuth 콜백 URL

## Testing
- 단위 테스트: `pytest tests/ -v`
- 수동 테스트: 삼성전자(005930) 90일 리포트 생성
- 카카오톡 테스트: `stock-report 005930 --period 30 --kakao`

## Error Handling
- 존재하지 않는 종목: 명확한 에러 메시지
- DART API 실패: graceful degradation (재무정보 없이 진행)
- 카카오 토큰 만료: 자동 갱신 시도
