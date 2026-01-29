# 한국 주식 분석 리포트 생성기 - 기술 스펙

## 1. 개요

### 1.1 목적
한국 주식의 다양한 데이터를 수집하고 분석하여 종합 리포트를 PDF로 생성, 카카오톡으로 자동 전송

### 1.2 핵심 기능
1. 주가/거래대금/등락률 조회 (pykrx)
2. 기술적 지표 계산 (RSI, TRIX, MACD)
3. DART 재무제표 조회 (YoY 비교)
4. 네이버 뉴스 수집 및 AI 분석
5. PDF 리포트 생성
6. 카카오톡 전송

---

## 2. 데이터 모델 (Pydantic)

### 2.1 StockInfo
```python
class StockInfo(BaseModel):
    code: str           # 종목코드 (6자리)
    name: str           # 종목명
    market: str         # 시장 (KOSPI/KOSDAQ)
```

### 2.2 PriceData
```python
class PriceData(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    trading_value: float  # 거래대금
    change_rate: float    # 등락률 (%)
```

### 2.3 TechnicalIndicators
```python
class TechnicalIndicators(BaseModel):
    date: date
    rsi: float | None
    trix: float | None
    trix_signal: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
```

### 2.4 Signal
```python
class Signal(BaseModel):
    indicator: str      # "RSI", "TRIX", "MACD"
    signal: str         # "BUY", "SELL", "HOLD"
    reason: str         # 시그널 발생 이유
    strength: int       # 1-5 강도
```

### 2.5 FinancialData
```python
class FinancialData(BaseModel):
    year: int
    quarter: str | None  # "Q1", "Q2", "Q3", "Q4", "Annual"
    revenue: float | None
    operating_income: float | None
    net_income: float | None
    per: float | None
    pbr: float | None
    roe: float | None
```

### 2.6 NewsArticle
```python
class NewsArticle(BaseModel):
    title: str
    link: str
    source: str         # 언론사
    published_at: datetime
    summary: str | None
```

### 2.7 AIAnalysis
```python
class AIAnalysis(BaseModel):
    news_summary: str           # 뉴스 핵심 요약
    sentiment: str              # "POSITIVE", "NEGATIVE", "NEUTRAL"
    sentiment_score: float      # -1.0 ~ 1.0
    key_issues: list[str]       # 주요 이슈 리스트
    overall_opinion: str        # 종합 의견
```

### 2.8 StockReport
```python
class StockReport(BaseModel):
    stock_info: StockInfo
    price_data: list[PriceData]
    indicators: list[TechnicalIndicators]
    signals: list[Signal]
    financials: list[FinancialData]
    news: list[NewsArticle]
    ai_analysis: AIAnalysis | None
    generated_at: datetime
    period_start: date
    period_end: date
```

---

## 3. 모듈별 상세 스펙

### 3.1 collectors/stock_price.py

#### 함수
```python
def get_stock_info(code: str) -> StockInfo:
    """종목 기본 정보 조회"""

def get_ohlcv(code: str, start: date, end: date) -> list[PriceData]:
    """OHLCV + 거래대금 + 등락률 조회"""

def get_fundamental(code: str, date: date) -> dict:
    """PER, PBR 등 기본 지표 조회"""
```

#### 사용 라이브러리
- `pykrx.stock`

### 3.2 collectors/dart.py

#### 함수
```python
def get_corp_code(stock_code: str) -> str | None:
    """종목코드 → DART 기업코드 변환"""

def get_financial_statements(
    corp_code: str,
    years: list[int]
) -> list[FinancialData]:
    """재무제표 조회 (복수 연도)"""

def get_company_overview(corp_code: str) -> dict:
    """기업 개황 정보"""
```

#### 데이터 범위
- 현재 연도 + 전년도 재무제표

### 3.3 collectors/news.py

#### 함수
```python
def search_news(
    keyword: str,
    months: int = 6
) -> list[NewsArticle]:
    """네이버 뉴스 검색 (최근 N개월)"""

def deduplicate_news(
    articles: list[NewsArticle],
    similarity_threshold: float = 0.8
) -> list[NewsArticle]:
    """제목 유사도 기반 중복 제거"""
```

#### 제약사항
- 최대 10건 반환
- 6개월 이내 기사만

### 3.4 indicators/technical.py

#### 함수
```python
def calculate_rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """RSI 계산"""

def calculate_trix(
    close: pd.Series,
    length: int = 15,
    signal: int = 9
) -> tuple[pd.Series, pd.Series]:
    """TRIX + 시그널 계산"""

def calculate_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD, 시그널, 히스토그램 계산"""

def generate_signals(
    indicators: list[TechnicalIndicators]
) -> list[Signal]:
    """매매 시그널 생성"""
```

#### 시그널 로직
| 지표 | 매수 | 매도 |
|------|------|------|
| RSI | < 30 | > 70 |
| TRIX | 시그널 상향 돌파 | 시그널 하향 돌파 |
| MACD | 시그널 상향 돌파 | 시그널 하향 돌파 |

### 3.5 analyzers/ai_analyzer.py

#### 함수
```python
def summarize_news(articles: list[NewsArticle]) -> str:
    """뉴스 핵심 요약 (OpenAI)"""

def analyze_sentiment(articles: list[NewsArticle]) -> tuple[str, float]:
    """감성 분석 (감성, 점수)"""

def generate_opinion(report_data: dict) -> str:
    """종합 의견 생성"""

def analyze(
    articles: list[NewsArticle],
    report_data: dict
) -> AIAnalysis:
    """전체 AI 분석 수행"""
```

### 3.6 analyzers/stock_analyzer.py

#### 함수
```python
def analyze(
    code: str,
    start: date,
    end: date,
    use_ai: bool = True
) -> StockReport:
    """종합 분석 수행 및 리포트 데이터 생성"""
```

### 3.7 reports/generator.py

#### 함수
```python
def create_price_chart(
    price_data: list[PriceData],
    output_path: Path
) -> Path:
    """가격 차트 생성 (matplotlib)"""

def create_indicator_chart(
    indicators: list[TechnicalIndicators],
    output_path: Path
) -> Path:
    """지표 차트 생성"""

def generate_pdf(
    report: StockReport,
    output_dir: Path
) -> Path:
    """PDF 리포트 생성"""
```

### 3.8 notifiers/uploader.py

#### 함수
```python
def authenticate() -> Credentials:
    """Google OAuth 인증"""

def upload_file(file_path: Path) -> str:
    """파일 업로드 → file_id 반환"""

def get_share_link(file_id: str) -> str:
    """공유 링크 생성"""
```

### 3.9 notifiers/kakao.py

#### 함수
```python
def get_access_token() -> str:
    """액세스 토큰 발급/갱신"""

def send_to_me(
    title: str,
    description: str,
    link_url: str
) -> bool:
    """나에게 보내기"""
```

---

## 4. CLI 인터페이스

### 4.1 메인 커맨드
```bash
stock-report [OPTIONS] CODES...
```

### 4.2 옵션
| 옵션 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--period`, `-p` | int | None | 최근 N일 |
| `--start`, `-s` | date | None | 시작일 |
| `--end`, `-e` | date | None | 종료일 |
| `--preset` | str | None | 1w/1m/3m/6m/1y |
| `--kakao`, `-k` | flag | False | 카카오톡 전송 |
| `--no-ai` | flag | False | AI 분석 제외 |
| `--output`, `-o` | path | ./output | 출력 디렉토리 |

### 4.3 기본 동작
옵션 없이 실행 시 1주 + 1개월 리포트 2개 생성

---

## 5. 환경 설정

### 5.1 config.py
```python
class Settings(BaseSettings):
    dart_api_key: str
    openai_api_key: str | None = None
    kakao_rest_api_key: str | None = None
    kakao_redirect_uri: str = "http://localhost:8080/callback"
    google_credentials_path: Path | None = None

    output_dir: Path = Path("./output")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
```

---

## 6. 에러 처리

### 6.1 예외 클래스
```python
class StockAnalyzerError(Exception):
    """기본 예외"""

class StockNotFoundError(StockAnalyzerError):
    """존재하지 않는 종목"""

class DataCollectionError(StockAnalyzerError):
    """데이터 수집 실패"""

class ReportGenerationError(StockAnalyzerError):
    """리포트 생성 실패"""
```

### 6.2 Graceful Degradation
- DART 실패 → 재무정보 없이 진행
- 뉴스 수집 실패 → 뉴스 섹션 제외
- AI 분석 실패 → AI 섹션 제외
- 카카오 전송 실패 → 로컬 파일만 생성

---

## 7. 테스트 계획

### 7.1 단위 테스트
- `test_collectors.py` - 데이터 수집기
- `test_indicators.py` - 기술적 지표
- `test_analyzers.py` - 분석기
- `test_reports.py` - 리포트 생성

### 7.2 통합 테스트
- `test_integration.py` - 전체 파이프라인

### 7.3 테스트 데이터
- 삼성전자 (005930) - KOSPI
- SK하이닉스 (000660) - KOSPI
- 카카오 (035720) - KOSPI
