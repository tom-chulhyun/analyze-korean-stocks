"""Google Drive 파일 업로더 (Service Account 방식)"""

from datetime import datetime
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from stock_analyzer.config import get_settings

# Google Drive API 스코프
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# 루트 폴더 이름
ROOT_FOLDER_NAME = "한국 주식 분석"


class GoogleDriveUploader:
    """Google Drive 업로더 (Service Account 방식)"""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._service = None
        self._folder_cache: dict[str, str] = {}  # 폴더 ID 캐시

    @property
    def is_available(self) -> bool:
        """Google Drive API 사용 가능 여부"""
        return self._settings.has_google_drive

    def authenticate(self) -> bool:
        """Service Account 인증"""
        if not self.is_available:
            return False

        try:
            credentials = service_account.Credentials.from_service_account_file(
                str(self._settings.google_service_account_path),
                scopes=SCOPES,
            )

            self._service = build("drive", "v3", credentials=credentials)
            return True

        except Exception as e:
            print(f"Google 인증 실패: {e}")
            return False

    def _find_folder(self, folder_name: str, parent_id: str | None = None) -> str | None:
        """폴더 ID 찾기 (공유받은 폴더 포함)"""
        if not self._service:
            return None

        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            # 공유받은 폴더도 검색하기 위해 includeItemsFromAllDrives, supportsAllDrives 추가
            results = self._service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            ).execute()

            files = results.get("files", [])
            return files[0]["id"] if files else None

        except Exception as e:
            print(f"폴더 검색 실패: {e}")
            return None

    def _create_folder(self, folder_name: str, parent_id: str | None = None) -> str | None:
        """폴더 생성 (공유받은 폴더 내에 생성)"""
        if not self._service:
            return None

        if not parent_id:
            print("Service Account는 공유받은 폴더 내에만 생성 가능합니다.")
            return None

        try:
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }

            folder = self._service.files().create(
                body=file_metadata,
                fields="id",
                supportsAllDrives=True,
            ).execute()

            return folder.get("id")

        except Exception as e:
            print(f"폴더 생성 실패: {e}")
            return None

    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> str | None:
        """폴더 찾기 또는 생성 (부모 폴더 필수)"""
        # 캐시 키 생성
        cache_key = f"{parent_id}:{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        folder_id = self._find_folder(folder_name, parent_id)
        if not folder_id:
            folder_id = self._create_folder(folder_name, parent_id)

        if folder_id:
            self._folder_cache[cache_key] = folder_id

        return folder_id

    def get_monthly_folder_id(self, year_month: str | None = None) -> str | None:
        """월별 폴더 ID 반환 (없으면 생성)

        구조: 한국 주식 분석/2026-01/

        주의: "한국 주식 분석" 폴더는 미리 생성하고 Service Account에 공유해야 함
        """
        if not self._service:
            if not self.authenticate():
                return None

        # 기본값: 현재 월
        if not year_month:
            year_month = datetime.now().strftime("%Y-%m")

        # 루트 폴더 찾기 (공유받은 폴더여야 함)
        root_folder_id = self._find_folder(ROOT_FOLDER_NAME)
        if not root_folder_id:
            print(f"❌ 루트 폴더 '{ROOT_FOLDER_NAME}'를 찾을 수 없습니다.")
            print(f"   Google Drive에서 '{ROOT_FOLDER_NAME}' 폴더를 생성하고")
            print(f"   Service Account 이메일에 공유(편집자)해주세요.")
            return None

        # 월별 폴더 찾기/생성
        monthly_folder_id = self._get_or_create_folder(year_month, root_folder_id)
        if not monthly_folder_id:
            print(f"월별 폴더 '{year_month}' 생성 실패")
            return None

        return monthly_folder_id

    def upload_file(self, file_path: Path, mime_type: str = "application/pdf", folder_id: str | None = None) -> str | None:
        """파일 업로드 (공유받은 폴더에 업로드)"""
        if not self._service:
            if not self.authenticate():
                return None

        if not folder_id:
            print("Service Account는 공유받은 폴더에만 업로드 가능합니다.")
            return None

        try:
            file_metadata = {
                "name": file_path.name,
                "parents": [folder_id],
            }

            media = MediaFileUpload(
                str(file_path),
                mimetype=mime_type,
                resumable=True,
            )

            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()

            return file.get("id")

        except Exception as e:
            print(f"파일 업로드 실패: {e}")
            return None

    def get_file_link(self, file_id: str) -> str | None:
        """파일 링크 반환 (폴더 공유 권한 사용자만 접근 가능)"""
        if not self._service:
            if not self.authenticate():
                return None

        try:
            file = self._service.files().get(
                fileId=file_id,
                fields="webViewLink",
                supportsAllDrives=True,
            ).execute()

            return file.get("webViewLink")

        except Exception as e:
            print(f"파일 링크 조회 실패: {e}")
            return None

    def share_with_user(self, file_id: str, email: str, role: str = "reader") -> bool:
        """특정 사용자에게 파일 공유

        Args:
            file_id: 파일 ID
            email: 공유할 사용자 이메일
            role: 권한 (reader, writer, commenter)

        Returns:
            성공 여부
        """
        if not self._service:
            if not self.authenticate():
                return False

        try:
            self._service.permissions().create(
                fileId=file_id,
                body={
                    "type": "user",
                    "role": role,
                    "emailAddress": email,
                },
                sendNotificationEmail=False,
            ).execute()
            return True

        except Exception as e:
            print(f"공유 설정 실패: {e}")
            return False

    def upload_to_drive(self, file_path: Path, year_month: str | None = None) -> tuple[str | None, str | None]:
        """파일 업로드 (폴더 공유 권한 사용자만 접근 가능)

        Args:
            file_path: 업로드할 파일 경로
            year_month: 월별 폴더명 (예: "2026-01"). None이면 현재 월 사용

        Returns:
            (파일 ID, 파일 링크) 튜플. 실패 시 (None, None)
        """
        # 월별 폴더 ID 가져오기
        folder_id = self.get_monthly_folder_id(year_month)
        if not folder_id:
            print("월별 폴더 생성 실패")
            return None, None

        file_id = self.upload_file(file_path, folder_id=folder_id)
        if not file_id:
            return None, None

        file_link = self.get_file_link(file_id)
        return file_id, file_link
