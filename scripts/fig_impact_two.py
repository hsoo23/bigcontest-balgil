"""발표 13장 · 보고서 9절 그림 — 사회적 영향력 두 지표(조기성 · 도달 효율).

**두 칸으로 꽉 채운다.** 규정의 세 지표 중 「기존 체계 보완율」은 동 단위 공개 경제 지표를
구하지 못해 내지 못했다(09절 9.1-1). 빈 세 번째 칸을 두면 못 낸 것이 그림의 주인공이 된다.
못 낸 사실은 발표 15장 한계에 적는다.

왼쪽 — 조기성. 시간 축 위에 격월 31.5일과 주간 3.0일을 찍고 간격을 화살표로 본다.
  **「다 잡는다」가 아니다**: 끊김 지속 중앙값이 2일이라 탐색일 전에 이미 끝난 건이
  격월 13.0건 · 주간에도 5.7건 남는다. 그래서 판정이 그날 상태가 아니라 7일 창이다.

오른쪽 — 도달 효율. **정의를 먼저 적는다.** 「공급 부족 ∩ 필요 큼」으로 고른 k개 동이
  **공급 부족 동 안의 무작위**보다 고령 1인세대에 몇 배 닿는가다. 기획안의 원래 정의
  (터전 하위 k개 ↔ 도시 전체 무작위)로는 춘천이 1배 아래라, 정의 없이 배수만 쓰면 어긋난다.

입력: data/reference/reach_efficiency.csv (저장소에 있음 — 원본 없이 그려진다)
      조기성 네 수는 scripts/explore_earliness.py 출력이자 최종수치표 6절 값이다.
      CSV 로 떨어지지 않아 EARLINESS 에 적고 그 자리에 출처를 남긴다.
출력: reports/figures/fig_impact_two.png
실행: python scripts/fig_impact_two.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "reference" / "reach_efficiency.csv"
OUT = ROOT / "reports" / "figures" / "fig_impact_two.png"

# scripts/explore_earliness.py 「실제 끊김 14건」 행 · 최종수치표 6절
EARLINESS = {"격월": 31.5, "주간": 3.0, "격월_최대": 54, "주간_최대": 6, "격월_놓침": 13.0, "주간_놓침": 5.7}
RULE = "우선순위"          # reach_efficiency.csv 의 「우선순위 (터전 하위 절반 ∩ 1인세대 많은 순)」

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
BAR, FAINT, GRID = "#3987e5", "#cde2fb", "#ececea"


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def main() -> None:
    korean_font()
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    p = d[d["규칙"].str.startswith(RULE)].sort_values(["도시", "k"])
    labels = [f"{r.도시} k={r.k}" for r in p.itertuples()]
    ratios = [float(r._6) for r in p.itertuples()]      # 「도달 효율」

    fig = plt.figure(figsize=(11.2, 5.6), facecolor=SURFACE)
    ax = fig.add_axes((0.045, 0.38, 0.425, 0.44))       # 왼쪽 — 조기성
    bx = fig.add_axes((0.575, 0.38, 0.368, 0.44))       # 오른쪽 — 도달 효율

    # ── 왼쪽: 하나의 시간 축 위 두 점
    ax.set_xlim(-2.5, 36); ax.set_ylim(-1.15, 1.25)
    ax.axhline(0, color=GRID, lw=2, zorder=1)
    ax.plot([EARLINESS["격월"]], [0], marker="o", ms=15, color=FAINT, zorder=3,
            markeredgecolor=BAR, markeredgewidth=1.6)
    ax.plot([EARLINESS["주간"]], [0], marker="|", ms=26, color=BAR, mew=4, zorder=3)
    ax.text(EARLINESS["주간"], 0.30, f"주간 루프\n{EARLINESS['주간']:.1f}일", ha="center", va="bottom",
            fontsize=11, color=INK, linespacing=1.6, fontweight="bold")
    ax.text(EARLINESS["격월"], 0.30, f"격월 탐색\n{EARLINESS['격월']:.1f}일", ha="center", va="bottom",
            fontsize=11, color=INK_2, linespacing=1.6)
    ax.annotate("", xy=(EARLINESS["주간"], -0.38), xytext=(EARLINESS["격월"], -0.38),
                arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.4))
    gap = EARLINESS["격월"] - EARLINESS["주간"]
    ax.text((EARLINESS["격월"] + EARLINESS["주간"]) / 2, -0.52,
            f"{gap:.1f}일 빠릅니다", ha="center", va="top", fontsize=11.5, color=INK, fontweight="bold")
    ax.text(0, -0.92,
            f"최대 지연도 {EARLINESS['격월_최대']:.0f}일 → {EARLINESS['주간_최대']:.0f}일",
            ha="left", va="center", fontsize=9, color=MUTED)
    ax.set_title("조기성 — 끊김이 생기고 며칠 만에 보는가", loc="left", fontsize=12.5, color=INK, pad=16)

    # ── 오른쪽: 네 칸(두 도시 × k) 막대 + 무작위 기준선 1배
    y = range(len(ratios))
    bx.barh(list(y), ratios, height=0.52, color=BAR, zorder=3)
    bx.axvline(1.0, color=INK_2, lw=1.4, ls=(0, (4, 3)), zorder=4)
    bx.text(1.0, len(ratios) - 0.32, "  공급 부족 동 안 무작위 = 1배",
            ha="left", va="bottom", fontsize=9, color=INK_2)
    for i, v in enumerate(ratios):
        bx.text(v + 0.035, i, f"{v:.2f}배", va="center", ha="left", fontsize=11.5, color=INK)
    bx.set_yticks(list(y), labels, fontsize=10.5, color=INK_2)
    bx.set_xlim(0, max(ratios) + 0.42)
    bx.set_xticks([])
    bx.invert_yaxis()
    bx.set_title("도달 효율 — 같은 수의 동으로 몇 배 닿는가", loc="left",
                 fontsize=12.5, color=INK, pad=16)

    for a in (ax, bx):
        a.tick_params(length=0)
        a.set_facecolor(SURFACE)
        for sp in a.spines.values():
            sp.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])

    # 「다 잡는다가 아님」과 정의 — 각 칸 아래에 작게
    fig.text(0.045, 0.235,
             f"**다 잡는다는 뜻이 아닙니다.** 끊김 지속 중앙값이 2일이라 탐색일 전에 이미 끝난 건이\n"
             f"격월 {EARLINESS['격월_놓침']:.1f}건 · 주간에도 {EARLINESS['주간_놓침']:.1f}건 남습니다. "
             f"그래서 판정이 그날 상태가 아니라 7일 창입니다.".replace("**", ""),
             fontsize=9, color=MUTED, linespacing=1.8, va="top")
    fig.text(0.575, 0.235,
             "고르는 규칙은 「공급 부족(터전 하위 절반) ∩ 고령 1인세대 많은 순」이고,\n"
             "견주는 상대는 공급 부족 동 안의 무작위입니다. 도시 전체와 견주면\n"
             "수가 달라집니다 — 정의를 먼저 말합니다.",
             fontsize=9, color=MUTED, linespacing=1.8, va="top")

    fig.text(0.045, 0.040,
             "출처: scripts/explore_earliness.py(실제 끊김 14건 기준) · data/reference/reach_efficiency.csv · "
             "최종수치표 6절. 「기존 체계 보완율」은 동 단위 공개 경제 지표를 구하지 못해 내지 않았습니다(09절 9.1-1).",
             fontsize=8.5, color=MUTED)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"저장: {OUT.relative_to(ROOT)}  —  조기성 {EARLINESS['격월']} → {EARLINESS['주간']}일 · "
          f"도달 효율 {min(ratios):.2f}~{max(ratios):.2f}배 {labels}")


if __name__ == "__main__":
    main()
