"""카카오톡 나에게 보내기"""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from stock_analyzer.config import get_settings


class KakaoNotifier:
    """카카오톡 알림 발송기"""

    AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
    TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    SEND_ME_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    @property
    def is_available(self) -> bool:
        """카카오톡 API 사용 가능 여부"""
        return self._settings.has_kakao

    @property
    def _token_path(self) -> Path:
        """토큰 저장 경로"""
        return self._settings.token_dir / "kakao_token.json"

    def authenticate(self) -> bool:
        """OAuth 인증 수행"""
        if not self.is_available:
            return False

        # 기존 토큰 로드 시도
        if self._load_token():
            # 토큰 유효성 검사 및 갱신
            if self._refresh_access_token():
                return True

        # 새로운 인증 수행
        auth_code = self._get_auth_code()
        if not auth_code:
            return False

        return self._exchange_code_for_token(auth_code)

    def _get_auth_code(self) -> str | None:
        """인증 코드 획득"""
        # 인증 URL 생성
        params = {
            "client_id": self._settings.kakao_rest_api_key,
            "redirect_uri": self._settings.kakao_redirect_uri,
            "response_type": "code",
            "scope": "talk_message",
        }
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"

        # 콜백 서버 설정
        auth_code = [None]  # 클로저에서 수정 가능하도록 리스트 사용

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)

                if "code" in query:
                    auth_code[0] = query["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication successful!</h1>"
                        b"<p>You can close this window.</p></body></html>"
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication failed</h1></body></html>"
                    )

            def log_message(self, format, *args):
                pass  # 로그 출력 억제

        # 리다이렉트 URI에서 포트 추출
        parsed_uri = urlparse(self._settings.kakao_redirect_uri)
        port = parsed_uri.port or 8080

        # 콜백 서버 시작
        server = HTTPServer(("localhost", port), CallbackHandler)
        server.timeout = 120  # 2분 타임아웃

        print(f"브라우저에서 카카오 로그인을 진행하세요...")
        webbrowser.open(auth_url)

        # 콜백 대기
        server.handle_request()
        server.server_close()

        return auth_code[0]

    def _exchange_code_for_token(self, auth_code: str) -> bool:
        """인증 코드를 토큰으로 교환"""
        try:
            response = requests.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._settings.kakao_rest_api_key,
                    "redirect_uri": self._settings.kakao_redirect_uri,
                    "code": auth_code,
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")

            self._save_token()
            return True

        except Exception as e:
            print(f"토큰 교환 실패: {e}")
            return False

    def _refresh_access_token(self) -> bool:
        """액세스 토큰 갱신"""
        if not self._refresh_token:
            return False

        try:
            response = requests.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._settings.kakao_rest_api_key,
                    "refresh_token": self._refresh_token,
                },
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            self._access_token = data.get("access_token")

            # 리프레시 토큰도 갱신된 경우
            if "refresh_token" in data:
                self._refresh_token = data["refresh_token"]

            self._save_token()
            return True

        except Exception:
            return False

    def _load_token(self) -> bool:
        """저장된 토큰 로드"""
        if not self._token_path.exists():
            return False

        try:
            with open(self._token_path) as f:
                data = json.load(f)
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                return bool(self._access_token)
        except Exception:
            return False

    def _save_token(self) -> None:
        """토큰 저장"""
        self._settings.token_dir.mkdir(parents=True, exist_ok=True)

        with open(self._token_path, "w") as f:
            json.dump(
                {
                    "access_token": self._access_token,
                    "refresh_token": self._refresh_token,
                },
                f,
            )

    def send_to_me(
        self,
        title: str,
        description: str,
        link_url: str | None = None,
    ) -> bool:
        """나에게 보내기"""
        if not self._access_token:
            if not self.authenticate():
                return False

        try:
            # 템플릿 객체 구성
            template_object = {
                "object_type": "feed",
                "content": {
                    "title": title,
                    "description": description,
                    "image_url": "https://via.placeholder.com/800x400/2962FF/FFFFFF?text=Stock+Report",
                    "link": {
                        "web_url": link_url or "https://github.com",
                        "mobile_web_url": link_url or "https://github.com",
                    },
                },
            }

            # 링크 버튼 추가
            if link_url:
                template_object["buttons"] = [
                    {
                        "title": "리포트 보기",
                        "link": {
                            "web_url": link_url,
                            "mobile_web_url": link_url,
                        },
                    },
                ]

            response = requests.post(
                self.SEND_ME_URL,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "template_object": json.dumps(template_object),
                },
                timeout=10,
            )
            response.raise_for_status()

            result = response.json()
            return result.get("result_code") == 0

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # 토큰 만료 - 갱신 시도
                if self._refresh_access_token():
                    return self.send_to_me(title, description, link_url)
            print(f"카카오톡 전송 실패: {e}")
            return False
        except Exception as e:
            print(f"카카오톡 전송 실패: {e}")
            return False
