"""CLI 진입점"""

from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from stock_analyzer.analyzers.stock_analyzer import StockAnalyzer
from stock_analyzer.collectors.stock_price import StockNotFoundError
from stock_analyzer.config import get_settings
from stock_analyzer.notifiers.kakao import KakaoNotifier
from stock_analyzer.notifiers.uploader import GoogleDriveUploader
from stock_analyzer.reports.generator import ReportGenerator

app = typer.Typer(
    name="stock-report",
    help="한국 주식 분석 리포트 생성기",
    add_completion=False,
)

console = Console()


def parse_preset(preset: str) -> int:
    """프리셋을 일수로 변환"""
    presets = {
        "1w": 7,
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "1y": 365,
    }
    return presets.get(preset.lower(), 30)


def generate_report_for_period(
    analyzer: StockAnalyzer,
    generator: ReportGenerator,
    code: str,
    days: int,
    output_dir: Path,
) -> Path | None:
    """특정 기간에 대한 리포트 생성"""
    end = date.today()
    start = end - timedelta(days=days)

    try:
        report = analyzer.analyze(code, start, end)
        pdf_path = generator.generate_pdf(report, output_dir)
        return pdf_path
    except StockNotFoundError as e:
        console.print(f"[red]오류: {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]리포트 생성 실패: {e}[/red]")
        return None


def send_kakao_notification(
    pdf_paths: list[Path],
    stock_name: str,
) -> bool:
    """카카오톡으로 리포트 전송"""
    settings = get_settings()

    # Google Drive 업로더
    uploader = GoogleDriveUploader()
    if not uploader.is_available:
        console.print("[yellow]⚠ Google Drive API가 설정되지 않았습니다.[/yellow]")
        console.print("  카카오톡 전송을 위해 Google Drive 설정이 필요합니다.")
        return False

    # 카카오 알림기
    notifier = KakaoNotifier()
    if not notifier.is_available:
        console.print("[yellow]⚠ 카카오톡 API가 설정되지 않았습니다.[/yellow]")
        return False

    success_count = 0

    for pdf_path in pdf_paths:
        console.print(f"\n[bold blue]파일 업로드 중: {pdf_path.name}[/bold blue]")

        # Google Drive에 업로드
        share_link = uploader.upload_and_share(pdf_path)
        if not share_link:
            console.print(f"[red]  ✗ 업로드 실패[/red]")
            continue

        console.print(f"[green]  ✓ 업로드 완료[/green]")

        # 카카오톡 전송
        console.print(f"[bold blue]카카오톡 전송 중...[/bold blue]")
        success = notifier.send_to_me(
            title=f"{stock_name} 분석 리포트",
            description=f"📊 {pdf_path.stem} 리포트가 생성되었습니다.",
            link_url=share_link,
        )

        if success:
            console.print(f"[green]  ✓ 전송 완료[/green]")
            success_count += 1
        else:
            console.print(f"[red]  ✗ 전송 실패[/red]")

    return success_count > 0


@app.command()
def main(
    codes: Annotated[
        list[str],
        typer.Argument(
            help="종목코드 (예: 005930 000660)",
        ),
    ],
    period: Annotated[
        Optional[int],
        typer.Option(
            "--period", "-p",
            help="최근 N일 (예: 90)",
        ),
    ] = None,
    start: Annotated[
        Optional[str],
        typer.Option(
            "--start", "-s",
            help="시작일 (YYYY-MM-DD)",
        ),
    ] = None,
    end: Annotated[
        Optional[str],
        typer.Option(
            "--end", "-e",
            help="종료일 (YYYY-MM-DD)",
        ),
    ] = None,
    preset: Annotated[
        Optional[str],
        typer.Option(
            "--preset",
            help="기간 프리셋 (1w/1m/3m/6m/1y)",
        ),
    ] = None,
    kakao: Annotated[
        bool,
        typer.Option(
            "--kakao", "-k",
            help="카카오톡으로 전송",
        ),
    ] = False,
    no_ai: Annotated[
        bool,
        typer.Option(
            "--no-ai",
            help="AI 분석 제외",
        ),
    ] = False,
    output: Annotated[
        Optional[Path],
        typer.Option(
            "--output", "-o",
            help="출력 디렉토리",
        ),
    ] = None,
) -> None:
    """
    한국 주식 분석 리포트를 생성합니다.

    기본 실행 시 1주 + 1개월 리포트 2개를 생성합니다.

    예시:
        stock-report 005930                    # 삼성전자 1주+1개월 리포트
        stock-report 005930 --period 90        # 90일 리포트
        stock-report 005930 --preset 3m        # 3개월 리포트
        stock-report 005930 --kakao            # 카카오톡 전송
    """
    settings = get_settings()

    # 출력 디렉토리 설정
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 분석기 및 생성기 초기화
    analyzer = StockAnalyzer(use_ai=not no_ai)
    generator = ReportGenerator()

    # 기간 결정
    periods: list[int] = []

    if start and end:
        # 시작일/종료일 지정
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        periods = [(end_date - start_date).days]
    elif period:
        periods = [period]
    elif preset:
        periods = [parse_preset(preset)]
    else:
        # 기본값: 1주 + 1개월
        periods = [7, 30]

    # 각 종목에 대해 리포트 생성
    for code in codes:
        console.print(Panel(f"[bold]종목 분석: {code}[/bold]", style="blue"))

        all_pdf_paths: list[Path] = []
        stock_name: str = ""

        for days in periods:
            console.print(f"\n[bold cyan]>>> {days}일 리포트 생성[/bold cyan]")

            pdf_path = generate_report_for_period(
                analyzer,
                generator,
                code,
                days,
                output_dir,
            )

            if pdf_path:
                all_pdf_paths.append(pdf_path)
                console.print(f"[green]✓ 리포트 생성 완료: {pdf_path}[/green]")

                # 종목명 저장 (카카오톡 전송용)
                if not stock_name:
                    try:
                        stock_name = analyzer.price_collector.get_stock_info(code).name
                    except Exception:
                        stock_name = code

        # 카카오톡 전송
        if kakao and all_pdf_paths:
            console.print(f"\n[bold cyan]>>> 카카오톡 전송[/bold cyan]")
            send_kakao_notification(all_pdf_paths, stock_name)

    console.print(f"\n[bold green]모든 작업 완료![/bold green]")
    console.print(f"리포트 저장 위치: {output_dir.absolute()}")


if __name__ == "__main__":
    app()
