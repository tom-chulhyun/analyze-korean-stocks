"""CLI 진입점"""

from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Optional

import typer
from pypdf import PdfWriter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stock_analyzer.analyzers.stock_analyzer import StockAnalyzer
from stock_analyzer.collectors.stock_price import StockNotFoundError, StockPriceCollector
from stock_analyzer.config import get_settings
from stock_analyzer.notifiers.github_uploader import GitHubUploader
from stock_analyzer.notifiers.kakao import KakaoNotifier
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


def select_top_stocks(top_n: int = 10, market: str = "ALL") -> list[dict]:
    """거래대금 상위 종목 자동 선정"""
    console.print(f"\n[bold blue]거래대금 상위 {top_n}개 종목 조회 중...[/bold blue]")

    collector = StockPriceCollector()
    stocks = []

    if market == "ALL":
        # KOSPI + KOSDAQ 합산
        kospi = collector.get_top_stocks_by_trading_value(top_n=top_n, market="KOSPI")
        kosdaq = collector.get_top_stocks_by_trading_value(top_n=top_n, market="KOSDAQ")
        combined = kospi + kosdaq
        # 거래대금 기준 정렬 후 상위 N개
        combined.sort(key=lambda x: x["trading_value"], reverse=True)
        stocks = combined[:top_n]
    else:
        stocks = collector.get_top_stocks_by_trading_value(top_n=top_n, market=market)

    if not stocks:
        console.print("[red]종목 조회 실패[/red]")
        return []

    # 선정된 종목 표시
    table = Table(title=f"선정된 종목 ({len(stocks)}개)")
    table.add_column("순위", justify="center", width=4)
    table.add_column("종목코드", justify="center", width=8)
    table.add_column("종목명", width=15)
    table.add_column("현재가", justify="right", width=10)
    table.add_column("등락률", justify="right", width=8)
    table.add_column("거래대금", justify="right", width=12)

    for i, stock in enumerate(stocks, 1):
        change_color = "green" if stock["change_rate"] >= 0 else "red"
        table.add_row(
            str(i),
            stock["code"],
            stock["name"],
            f"{stock['close']:,}원",
            f"[{change_color}]{stock['change_rate']:+.2f}%[/{change_color}]",
            f"{stock['trading_value'] / 100_000_000:,.0f}억",
        )

    console.print(table)
    return stocks


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


def merge_pdfs(pdf_paths: list[Path], output_path: Path, delete_originals: bool = False) -> Path:
    """여러 PDF를 하나로 합치기"""
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        writer.append(str(pdf_path))

    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    # 원본 파일 삭제
    if delete_originals:
        for pdf_path in pdf_paths:
            try:
                pdf_path.unlink()
            except Exception:
                pass

    return output_path


def cleanup_old_reports(output_dir: Path, max_reports: int = 10) -> None:
    """오래된 리포트 삭제 (최신 N개만 유지)"""
    pdf_files = list(output_dir.glob("*.pdf"))

    if len(pdf_files) <= max_reports:
        return

    # 수정 시간 기준 정렬 (오래된 것 먼저)
    pdf_files.sort(key=lambda f: f.stat().st_mtime)

    # 삭제할 파일 수
    files_to_delete = pdf_files[: len(pdf_files) - max_reports]

    for pdf_path in files_to_delete:
        try:
            pdf_path.unlink()
            console.print(f"[dim]🗑 오래된 리포트 삭제: {pdf_path.name}[/dim]")
        except Exception:
            pass


def send_kakao_notification(
    pdf_paths: list[Path],
    stock_name: str,
) -> bool:
    """카카오톡으로 리포트 알림 전송 (GitHub 링크 포함)"""
    # 카카오 알림기
    notifier = KakaoNotifier()
    if not notifier.is_available:
        console.print("[yellow]⚠ 카카오톡 API가 설정되지 않았습니다.[/yellow]")
        return False

    # GitHub 업로더
    uploader = GitHubUploader(max_reports=10)
    if not uploader.is_available:
        console.print("[yellow]⚠ Git 저장소를 찾을 수 없습니다.[/yellow]")
        return False

    # GitHub에 업로드
    console.print(f"\n[bold blue]GitHub에 업로드 중...[/bold blue]")
    success, links = uploader.upload_reports(pdf_paths)

    if not success or not links:
        console.print(f"[red]  ✗ 업로드 실패[/red]")
        return False

    console.print(f"[green]  ✓ 업로드 완료[/green]")

    # 카카오톡 전송
    console.print(f"[bold blue]카카오톡 전송 중...[/bold blue]")

    # 첫 번째 링크 사용
    link = links[0] if links else None
    file_names = ", ".join(p.stem for p in pdf_paths)

    success = notifier.send_to_me(
        title=f"{stock_name} 분석 리포트",
        description=f"📊 {file_names} 리포트가 생성되었습니다.",
        link_url=link,
    )

    if success:
        console.print(f"[green]  ✓ 전송 완료[/green]")
        return True
    else:
        console.print(f"[red]  ✗ 전송 실패[/red]")
        return False


@app.command()
def main(
    codes: Annotated[
        Optional[list[str]],
        typer.Argument(
            help="종목코드 (예: 005930 000660). 미입력 시 자동 선정",
        ),
    ] = None,
    top_n: Annotated[
        int,
        typer.Option(
            "--top", "-n",
            help="자동 선정 시 상위 N개 종목",
        ),
    ] = 10,
    market: Annotated[
        str,
        typer.Option(
            "--market", "-m",
            help="시장 선택 (KOSPI/KOSDAQ/ALL)",
        ),
    ] = "ALL",
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

    종목코드 미입력 시 거래대금 상위 종목을 자동으로 선정합니다.
    2개 이상의 종목 분석 시 자동으로 하나의 PDF로 병합됩니다.

    예시:
        stock-report                           # 거래대금 상위 10개 종목 자동 분석 (병합)
        stock-report --top 5                   # 상위 5개 종목 (병합)
        stock-report --market KOSDAQ           # KOSDAQ만
        stock-report 005930 000660             # 지정 종목 분석 (병합)
        stock-report 005930 --period 90        # 90일 리포트 (단일)
        stock-report --kakao                   # 자동 선정 + 카카오톡 전송
    """
    settings = get_settings()

    # 출력 디렉토리 설정
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 종목 결정
    if codes:
        # 수동 입력된 종목 사용
        stock_list = [{"code": c, "name": c} for c in codes]
    else:
        # 자동 종목 선정
        stock_list = select_top_stocks(top_n=top_n, market=market.upper())
        if not stock_list:
            raise typer.Exit(1)

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
        # 기본값: 1개월
        periods = [30]

    all_pdf_paths: list[Path] = []

    # 각 종목에 대해 리포트 생성
    for i, stock in enumerate(stock_list, 1):
        code = stock["code"]
        name = stock.get("name", code)

        console.print(Panel(
            f"[bold]({i}/{len(stock_list)}) {name} ({code})[/bold]",
            style="blue"
        ))

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

    # PDF 병합 (2개 이상일 경우 자동 병합)
    merged_pdf: Path | None = None
    if len(all_pdf_paths) > 1:
        console.print(f"\n[bold cyan]>>> PDF 병합 중...[/bold cyan]")
        today_str = date.today().strftime("%Y%m%d")
        merged_filename = f"stock_report_{today_str}.pdf"
        merged_path = output_dir / merged_filename
        merged_pdf = merge_pdfs(all_pdf_paths, merged_path, delete_originals=True)
        console.print(f"[green]✓ 병합 완료: {merged_pdf}[/green]")
        console.print(f"[dim]  (개별 PDF {len(all_pdf_paths)}개 삭제됨)[/dim]")

    # 카카오톡 전송 (병합된 파일 또는 전체 리포트)
    if kakao and all_pdf_paths:
        console.print(f"\n[bold cyan]>>> 카카오톡 전송[/bold cyan]")
        files_to_send = [merged_pdf] if merged_pdf else all_pdf_paths
        send_kakao_notification(files_to_send, f"{len(all_pdf_paths)}개 종목")

    # 오래된 리포트 정리 (최대 10개 유지)
    cleanup_old_reports(output_dir, max_reports=10)

    console.print(f"\n[bold green]모든 작업 완료![/bold green]")
    if merged_pdf:
        console.print(f"병합된 파일: {merged_pdf.name}")
    else:
        console.print(f"생성된 리포트: {len(all_pdf_paths)}개")
    console.print(f"저장 위치: {output_dir.absolute()}")


if __name__ == "__main__":
    app()
