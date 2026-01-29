"""PDF 리포트 생성기"""

import base64
import platform
from datetime import date
from io import BytesIO
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from stock_analyzer.models import PriceData, StockReport, TechnicalIndicators

# 백엔드 설정 (GUI 없이 사용)
matplotlib.use("Agg")

# 한글 폰트 설정 (플랫폼별 자동 감지)
def _setup_korean_font() -> None:
    """플랫폼에 맞는 한글 폰트 설정"""
    system = platform.system()

    if system == "Darwin":  # macOS
        font_candidates = ["AppleGothic", "Apple SD Gothic Neo"]
    elif system == "Windows":
        font_candidates = ["Malgun Gothic", "맑은 고딕"]
    else:  # Linux (Ubuntu)
        font_candidates = ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]

    # 사용 가능한 폰트 찾기
    from matplotlib import font_manager
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}

    for font in font_candidates:
        if font in available_fonts:
            plt.rcParams["font.family"] = font
            break
    else:
        # 폰트를 찾지 못한 경우 기본 sans-serif 사용
        plt.rcParams["font.family"] = "sans-serif"

    plt.rcParams["axes.unicode_minus"] = False

_setup_korean_font()


class ReportGenerator:
    """PDF 리포트 생성기"""

    def __init__(self) -> None:
        template_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def generate_pdf(
        self,
        report: StockReport,
        output_dir: Path,
    ) -> Path:
        """PDF 리포트 생성"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        period_days = (report.period_end - report.period_start).days
        if period_days <= 7:
            period_suffix = "1w"
        elif period_days <= 31:
            period_suffix = "1m"
        elif period_days <= 93:
            period_suffix = "3m"
        elif period_days <= 186:
            period_suffix = "6m"
        else:
            period_suffix = "1y"

        filename = f"{report.stock_info.code}_{period_suffix}_{report.period_end.strftime('%Y%m%d')}.pdf"
        output_path = output_dir / filename

        # 차트 생성
        price_chart = self._create_price_chart(report.price_data)
        indicator_chart = self._create_indicator_chart(report.indicators)

        # 템플릿 렌더링
        template = self._env.get_template("report.html")
        html_content = template.render(
            report=report,
            price_chart=price_chart,
            indicator_chart=indicator_chart,
            format_number=self._format_number,
            format_percent=self._format_percent,
            format_date=self._format_date,
            truncate_text=self._truncate_text,
        )

        # PDF 생성
        HTML(string=html_content).write_pdf(str(output_path))

        return output_path

    def _create_price_chart(self, price_data: list[PriceData]) -> str:
        """가격 차트 생성 (Base64 인코딩)"""
        if not price_data:
            return ""

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), height_ratios=[3, 1])
        fig.patch.set_facecolor("white")

        dates = [p.date for p in price_data]
        closes = [p.close for p in price_data]
        volumes = [p.volume for p in price_data]

        # 가격 차트
        ax1.plot(dates, closes, color="#2962FF", linewidth=1.5)
        ax1.fill_between(dates, closes, alpha=0.1, color="#2962FF")
        ax1.set_ylabel("종가 (원)", fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_title("주가 추이", fontsize=12, fontweight="bold")

        # 거래량 차트
        colors = ["#26A69A" if i == 0 or closes[i] >= closes[i - 1] else "#EF5350" for i in range(len(closes))]
        ax2.bar(dates, volumes, color=colors, alpha=0.7)
        ax2.set_ylabel("거래량", fontsize=10)
        ax2.grid(True, alpha=0.3)

        # x축 날짜 포맷
        fig.autofmt_xdate()
        plt.tight_layout()

        # Base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight", facecolor="white")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)

        return f"data:image/png;base64,{image_base64}"

    def _create_indicator_chart(self, indicators: list[TechnicalIndicators]) -> str:
        """기술적 지표 차트 생성 (Base64 인코딩)"""
        if not indicators:
            return ""

        fig, axes = plt.subplots(3, 1, figsize=(10, 8))
        fig.patch.set_facecolor("white")

        dates = [ind.date for ind in indicators]

        # None을 NaN으로 변환하는 헬퍼 함수
        def safe_values(values: list) -> list:
            import numpy as np
            return [v if v is not None else np.nan for v in values]

        # RSI 차트
        rsi_values = safe_values([ind.rsi for ind in indicators])
        ax_rsi = axes[0]
        ax_rsi.plot(dates, rsi_values, color="#7C4DFF", linewidth=1.5, label="RSI")
        ax_rsi.axhline(y=70, color="#EF5350", linestyle="--", alpha=0.7, label="과매수 (70)")
        ax_rsi.axhline(y=30, color="#26A69A", linestyle="--", alpha=0.7, label="과매도 (30)")
        ax_rsi.fill_between(dates, 30, 70, alpha=0.1, color="gray")
        ax_rsi.set_ylabel("RSI", fontsize=10)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.legend(loc="upper left", fontsize=8)
        ax_rsi.grid(True, alpha=0.3)
        ax_rsi.set_title("RSI (14)", fontsize=11, fontweight="bold")

        # TRIX 차트
        trix_values = safe_values([ind.trix for ind in indicators])
        trix_signal_values = safe_values([ind.trix_signal for ind in indicators])
        ax_trix = axes[1]
        ax_trix.plot(dates, trix_values, color="#2962FF", linewidth=1.5, label="TRIX")
        ax_trix.plot(dates, trix_signal_values, color="#FF6D00", linewidth=1.5, label="Signal")
        ax_trix.axhline(y=0, color="gray", linestyle="-", alpha=0.5)
        ax_trix.set_ylabel("TRIX", fontsize=10)
        ax_trix.legend(loc="upper left", fontsize=8)
        ax_trix.grid(True, alpha=0.3)
        ax_trix.set_title("TRIX (15, 9)", fontsize=11, fontweight="bold")

        # MACD 차트
        macd_values = safe_values([ind.macd for ind in indicators])
        macd_signal_values = safe_values([ind.macd_signal for ind in indicators])
        macd_hist_values = safe_values([ind.macd_histogram for ind in indicators])
        ax_macd = axes[2]

        # 히스토그램 (NaN을 0으로 처리하여 bar 차트 그리기)
        import numpy as np
        hist_for_bar = [0 if np.isnan(h) else h for h in macd_hist_values]
        colors = ["#26A69A" if h >= 0 else "#EF5350" for h in hist_for_bar]
        ax_macd.bar(dates, hist_for_bar, color=colors, alpha=0.5, label="Histogram")
        ax_macd.plot(dates, macd_values, color="#2962FF", linewidth=1.5, label="MACD")
        ax_macd.plot(dates, macd_signal_values, color="#FF6D00", linewidth=1.5, label="Signal")
        ax_macd.axhline(y=0, color="gray", linestyle="-", alpha=0.5)
        ax_macd.set_ylabel("MACD", fontsize=10)
        ax_macd.legend(loc="upper left", fontsize=8)
        ax_macd.grid(True, alpha=0.3)
        ax_macd.set_title("MACD (12, 26, 9)", fontsize=11, fontweight="bold")

        # x축 날짜 포맷
        fig.autofmt_xdate()
        plt.tight_layout()

        # Base64 인코딩
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight", facecolor="white")
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)

        return f"data:image/png;base64,{image_base64}"

    @staticmethod
    def _format_number(value: float | int | None) -> str:
        """숫자 포맷팅 (천 단위 콤마)"""
        if value is None:
            return "-"
        if isinstance(value, float):
            if abs(value) >= 1_000_000_000_000:  # 조 단위
                return f"{value / 1_000_000_000_000:.2f}조"
            elif abs(value) >= 100_000_000:  # 억 단위
                return f"{value / 100_000_000:.0f}억"
            elif abs(value) >= 10_000:  # 만 단위
                return f"{value / 10_000:.0f}만"
            else:
                return f"{value:,.0f}"
        return f"{value:,}"

    @staticmethod
    def _format_percent(value: float | None) -> str:
        """퍼센트 포맷팅"""
        if value is None:
            return "-"
        return f"{value:+.2f}%"

    @staticmethod
    def _format_date(value: date) -> str:
        """날짜 포맷팅"""
        return value.strftime("%Y-%m-%d")

    @staticmethod
    def _truncate_text(text: str | None, max_length: int = 300) -> str:
        """텍스트 잘라내기 (PDF 렌더링용)"""
        if not text:
            return ""
        # 특수 문자 제거 및 텍스트 정리
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."
