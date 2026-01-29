# API 설정 가이드

## 1. DART API (필수)

### 1.1 API 키 발급
1. [DART 오픈API](https://opendart.fss.or.kr/) 접속
2. 회원가입 및 로그인
3. 인증키 신청
4. 발급된 키를 `.env`에 저장

### 1.2 환경변수
```
DART_API_KEY=your_dart_api_key_here
```

---

## 2. OpenAI API (선택)

### 2.1 API 키 발급
1. [OpenAI Platform](https://platform.openai.com/) 접속
2. 계정 생성 및 로그인
3. API Keys 메뉴에서 새 키 생성
4. 발급된 키를 `.env`에 저장

### 2.2 환경변수
```
OPENAI_API_KEY=sk-...
```

### 2.3 사용 모델
- 뉴스 요약: `gpt-4o-mini`
- 감성 분석: `gpt-4o-mini`
- 종합 의견: `gpt-4o-mini`

### 2.4 비용
- gpt-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens
- 리포트 1건당 예상 비용: ~$0.01

---

## 3. 네이버 검색 API (선택)

### 3.1 애플리케이션 등록
1. [네이버 개발자센터](https://developers.naver.com/) 접속
2. Application > 애플리케이션 등록
3. 애플리케이션 이름: `stock-analyzer`
4. 사용 API: **검색** 선택

### 3.2 API 키 확인
1. 내 애플리케이션 목록에서 생성된 앱 클릭
2. **Client ID**와 **Client Secret** 복사

### 3.3 환경변수
```
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

### 3.4 일일 할당량
- 검색 API: 25,000건/일

---

## 4. 카카오 API (선택)

### 4.1 애플리케이션 등록
1. [카카오 디벨로퍼스](https://developers.kakao.com/) 접속
2. 로그인 후 "내 애플리케이션" → "애플리케이션 추가하기"
3. 앱 이름: `stock-analyzer` (임의)
4. 사업자명: 개인 이름

### 4.2 REST API 키 확인
1. 생성된 앱 클릭
2. "앱 키" 메뉴
3. **REST API 키** 복사

### 4.3 카카오 로그인 설정
1. "카카오 로그인" 메뉴
2. "활성화 설정" → ON
3. "동의항목" 설정:
   - "카카오톡 메시지 전송" → "선택 동의" 체크

### 4.4 Redirect URI 등록
1. "카카오 로그인" → "Redirect URI"
2. 추가: `http://localhost:8080/callback`

### 5.5 환경변수
```
KAKAO_REST_API_KEY=your_rest_api_key
KAKAO_REDIRECT_URI=http://localhost:8080/callback
```

### 5.6 최초 인증 (CLI 실행 시 자동)
1. `stock-report 005930 --kakao` 실행
2. 브라우저에서 카카오 로그인
3. 권한 동의
4. 토큰이 `~/.stock-analyzer/kakao_token.json`에 저장됨

---

## 5. Google Drive API (선택)

### 5.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성: `stock-analyzer`

### 5.2 API 활성화
1. "API 및 서비스" → "라이브러리"
2. "Google Drive API" 검색 및 활성화

### 5.3 OAuth 동의 화면 설정
1. "OAuth 동의 화면" 메뉴
2. User Type: 외부
3. 앱 정보 입력:
   - 앱 이름: `stock-analyzer`
   - 사용자 지원 이메일: 본인 이메일
   - 개발자 연락처: 본인 이메일
4. 범위(Scopes):
   - `https://www.googleapis.com/auth/drive.file`
5. 테스트 사용자에 본인 계정 추가

### 5.4 OAuth 클라이언트 ID 생성
1. "사용자 인증 정보" → "사용자 인증 정보 만들기"
2. "OAuth 클라이언트 ID"
3. 애플리케이션 유형: **데스크톱 앱**
4. 이름: `stock-analyzer-cli`
5. JSON 다운로드

### 5.5 환경변수
```
GOOGLE_CREDENTIALS_PATH=./credentials.json
```
- 다운로드한 JSON 파일을 프로젝트 루트에 `credentials.json`으로 저장

### 5.6 최초 인증 (CLI 실행 시 자동)
1. `stock-report 005930 --kakao` 실행
2. 브라우저에서 Google 로그인
3. 권한 동의
4. 토큰이 `~/.stock-analyzer/google_token.json`에 저장됨

---

## 6. 환경변수 요약

### .env 파일
```env
# 필수
DART_API_KEY=your_dart_api_key

# 선택 - AI 분석
OPENAI_API_KEY=sk-...

# 선택 - 카카오톡 전송
KAKAO_REST_API_KEY=your_kakao_rest_api_key
KAKAO_REDIRECT_URI=http://localhost:8080/callback

# 선택 - Google Drive 업로드
GOOGLE_CREDENTIALS_PATH=./credentials.json
```

---

## 7. 기능별 API 의존성

| 기능 | 필요 API |
|------|----------|
| 주가 조회 | 없음 (pykrx) |
| 기술적 지표 | 없음 |
| 재무제표 | DART API |
| 뉴스 수집 | 없음 (네이버 크롤링) |
| AI 분석 | OpenAI API |
| PDF 생성 | 없음 |
| 카카오톡 전송 | 카카오 + Google Drive |

### Graceful Degradation
- API 키 없으면 해당 기능 자동 비활성화
- DART 키 없어도 주가/지표 분석 가능
- OpenAI 키 없으면 AI 분석 섹션 제외
- 카카오/구글 키 없으면 로컬 PDF만 생성
