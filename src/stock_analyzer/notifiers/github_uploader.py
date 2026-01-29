"""GitHub Repository 파일 업로더 (현재 레포 사용)"""

import os
import subprocess
from pathlib import Path
import shutil

from stock_analyzer.config import get_settings


class GitHubUploader:
    """현재 Repository의 reports/ 폴더에 파일 업로드 (최신 N개 유지)"""

    def __init__(self, max_reports: int = 10) -> None:
        self._settings = get_settings()
        self._max_reports = max_reports
        self._repo_root = self._find_repo_root()
        self._setup_git_config()

    def _find_repo_root(self) -> Path | None:
        """Git 레포지토리 루트 찾기"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            pass
        return None

    def _setup_git_config(self) -> None:
        """Git config 설정 (GitHub Actions 환경 지원)"""
        if not self._repo_root:
            return

        # GitHub Actions 환경인지 확인
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # GitHub Actions bot으로 설정
            self._run_git("config", "user.name", "github-actions[bot]")
            self._run_git("config", "user.email", "github-actions[bot]@users.noreply.github.com")

    @property
    def is_available(self) -> bool:
        """GitHub 업로드 사용 가능 여부"""
        return self._repo_root is not None

    @property
    def reports_dir(self) -> Path | None:
        """리포트 저장 디렉토리"""
        if self._repo_root:
            return self._repo_root / "reports"
        return None

    def _run_git(self, *args: str) -> tuple[bool, str]:
        """Git 명령 실행"""
        if not self._repo_root:
            return False, "Repository를 찾을 수 없습니다."

        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self._repo_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return False, result.stderr
            return True, result.stdout
        except subprocess.TimeoutExpired:
            return False, "Git 명령 타임아웃"
        except Exception as e:
            return False, str(e)

    def _get_remote_url(self) -> str | None:
        """Remote URL에서 repo 정보 추출"""
        success, output = self._run_git("remote", "get-url", "origin")
        if success:
            url = output.strip()
            # https://github.com/user/repo.git 또는 git@github.com:user/repo.git
            if "github.com" in url:
                if url.startswith("https://"):
                    # https://github.com/user/repo.git
                    repo = url.replace("https://github.com/", "").replace(".git", "")
                elif url.startswith("git@"):
                    # git@github.com:user/repo.git
                    repo = url.replace("git@github.com:", "").replace(".git", "")
                else:
                    return None
                return repo
        return None

    def _cleanup_old_reports(self) -> int:
        """오래된 리포트 삭제 (최신 N개만 유지)

        Returns:
            삭제된 파일 수
        """
        if not self.reports_dir or not self.reports_dir.exists():
            return 0

        # PDF 파일 목록 (수정 시간 기준 정렬)
        pdf_files = sorted(
            self.reports_dir.glob("*.pdf"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,  # 최신 순
        )

        # 최신 N개 제외하고 삭제
        files_to_delete = pdf_files[self._max_reports:]
        for f in files_to_delete:
            f.unlink()

        return len(files_to_delete)

    def upload_reports(
        self,
        pdf_paths: list[Path],
        commit_message: str | None = None,
    ) -> tuple[bool, list[str]]:
        """리포트 업로드 (최신 N개 유지)

        Args:
            pdf_paths: 업로드할 PDF 파일 경로 목록
            commit_message: 커밋 메시지 (기본값: 자동 생성)

        Returns:
            (성공 여부, 파일 링크 목록)
        """
        if not self.is_available:
            print("❌ Git repository를 찾을 수 없습니다.")
            return False, []

        if not pdf_paths:
            print("❌ 업로드할 파일이 없습니다.")
            return False, []

        # 1. reports 폴더 생성
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 2. 새 파일 복사
        print(f"📄 리포트 복사 중... ({len(pdf_paths)}개)")
        for pdf_path in pdf_paths:
            if pdf_path.exists():
                dest = self.reports_dir / pdf_path.name
                shutil.copy(pdf_path, dest)
                print(f"   → {pdf_path.name}")

        # 3. 오래된 리포트 삭제
        deleted_count = self._cleanup_old_reports()
        if deleted_count > 0:
            print(f"🗑️  오래된 리포트 삭제: {deleted_count}개 (최신 {self._max_reports}개 유지)")

        # 4. Git add
        success, _ = self._run_git("add", "reports/")
        if not success:
            print("❌ Git add 실패")
            return False, []

        # 5. 변경사항 확인 (untracked 파일 포함)
        success, status = self._run_git("status", "--porcelain", "-uall", "reports/")
        if not status.strip():
            print("ℹ️  변경사항 없음")
            return True, self._get_file_links(pdf_paths)

        # 6. Commit
        if not commit_message:
            file_names = ", ".join(p.stem for p in pdf_paths)
            commit_message = f"📊 리포트 업데이트: {file_names}"

        success, error = self._run_git("commit", "-m", commit_message)
        if not success:
            print(f"❌ Commit 실패: {error}")
            return False, []

        # 7. Push
        print(f"📤 Push 중...")
        success, error = self._run_git("push")
        if not success:
            print(f"❌ Push 실패: {error}")
            return False, []

        print("✅ 업로드 완료!")
        return True, self._get_file_links(pdf_paths)

    def _get_file_links(self, pdf_paths: list[Path]) -> list[str]:
        """파일 링크 생성"""
        repo = self._get_remote_url()
        if not repo:
            return [str(self.reports_dir / p.name) for p in pdf_paths]

        links = []
        for pdf_path in pdf_paths:
            # GitHub raw 링크
            link = f"https://github.com/{repo}/raw/main/reports/{pdf_path.name}"
            links.append(link)
        return links

    def upload_report(
        self,
        pdf_path: Path,
        commit_message: str | None = None,
    ) -> tuple[bool, str | None]:
        """단일 리포트 업로드

        Args:
            pdf_path: 업로드할 PDF 파일 경로
            commit_message: 커밋 메시지

        Returns:
            (성공 여부, 파일 링크)
        """
        success, links = self.upload_reports([pdf_path], commit_message)
        return success, links[0] if links else None

    def list_reports(self) -> list[Path]:
        """현재 저장된 리포트 목록 (최신 순)"""
        if not self.reports_dir or not self.reports_dir.exists():
            return []

        return sorted(
            self.reports_dir.glob("*.pdf"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
