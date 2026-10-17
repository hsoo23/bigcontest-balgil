"""발표 4장 · 보고서 4.1 그림 ① — 36칸 체류 비중 히트맵 (도시 × 성 × 연령).

도시마다 따로 그리고 **색 눈금도 도시마다 따로** 둔다. 강남 카드는 「강남에서 쓴 서울 거주자」의 결제라
춘천과 수준을 맞대지 않는다(실행계획 1-2절). 그래서 한 눈금에 두 도시를 올리지 않는다.
색은 크기 하나만 나타내므로 한 색상(파랑)의 연한→진한 순차 눈금이다.

입력: reanalysis/reference/features_segment.csv (저장소에 있음 — 원본 없이 그려진다)
출력: reports/figures/fig_stay_heatmap.png
실행: python scripts/fig_stay_heatmap.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reanalysis" / "reference" / "features_segment.csv"
OUT = ROOT / "reports" / "figures" / "fig_stay_heatmap.png"

AGES = ["10대", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대"]
SEXES = ["남성", "여성"]
CITIES = ["강남", "춘천"]

# 순차 눈금(파랑 100 → 700)과 글자·바탕색 — dataviz 기본 팔레트
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
LIGHT_TEXT_FROM = 4  # 눈금 7단계 중 이 단계부터 칸 안 글자를 흰색으로


def main() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next((n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"]
                                        if n in have), "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    cmap = LinearSegmentedColormap.from_list("blue_seq", BLUE)

    fig, axes = plt.subplots(2, 1, figsize=(9.6, 5.4), facecolor=SURFACE)
    for ax, city in zip(axes, CITIES):
        grid = d[d["city"] == city].pivot(index="sex", columns="AGE", values="stay").loc[SEXES, AGES]
        lo, hi = grid.values.min(), grid.values.max()
        im = ax.imshow(grid.values, cmap=cmap, vmin=lo, vmax=hi, aspect="auto")
        for i in range(len(SEXES)):
            for j in range(len(AGES)):
                v = grid.values[i, j]
                step = int((v - lo) / (hi - lo) * (len(BLUE) - 1) + 0.5)
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=10,
                        color="white" if step >= LIGHT_TEXT_FROM else INK)
        # 칸 사이 2px 바탕색 간격
        ax.set_xticks([x - 0.5 for x in range(1, len(AGES))], minor=True)
        ax.set_yticks([0.5], minor=True)
        ax.grid(which="minor", color=SURFACE, linewidth=2)
        ax.tick_params(which="minor", length=0)
        ax.set_xticks(range(len(AGES)), AGES, fontsize=10, color=INK_2)
        ax.set_yticks(range(len(SEXES)), SEXES, fontsize=10, color=INK_2)
        ax.tick_params(which="major", length=0)
        for s in ax.spines.values():
            s.set_visible(False)
        # 60대 이상(끊김 감시 · 순위 대상) 칸 묶음 표시
        ax.annotate("", xy=(4.55, -0.62), xytext=(8.45, -0.62), xycoords="data",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=1), annotation_clip=False)
        ax.text(6.5, -0.72, "60대 이상", ha="center", va="bottom", fontsize=9, color=MUTED)
        ax.set_title(f"{city} — 체류 비중(%)", loc="left", fontsize=12, color=INK, pad=18)
        cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
        cb.outline.set_visible(False)
        cb.ax.tick_params(labelsize=8, colors=MUTED, length=0)
        ax.set_facecolor(SURFACE)

    fig.text(0.01, 0.015, "출처: 신한카드 제공 데이터, 2025.7~12 · 거주자 결제 건수 기준 · 체류 업종 11개 ÷ 전 업종. "
             "색 눈금은 도시마다 따로입니다 — 두 도시의 수준을 맞대지 않습니다.",
             fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
