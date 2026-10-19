"""발표 7장 · 보고서 7.3 그림 — 보정 3단계의 헛알림 (0) → (1) → (2).

이 장의 주장은 둘이다.

  ① **한 단계만 켜면 오히려 늘어난다** — (1) 계절형 보정에서 131 → 150. 계절형만으로는
     공통 사건(명절·큰비)을 못 지우고, 기준선이 낮아져 알림이 늘어난다. (2) 같은 도시
     30·40대 편차 차감까지 켜야 44로 준다. 그래서 (1)이 (0)보다 **높게** 보여야 한다.
  ② **한 주만 떼어 봐도 같은 모양이다** — 시연 주(10/06~10/12, 추석) 경보일 71 → 72 → 23.

병원·약국 분리는 **세 번째 단계가 아니다.** 같은 3단계를 대상 업종만 바꿔 다시 잰 다른 축이라
(수치표 3절이 표 둘로 나뉜다) 같은 축에 흐린 선으로 겹쳐 둔다. 세 단계로 그리면
"병원·약국을 빼는 것이 보정"으로 읽힌다(#65, 10/15 고침).

입력: reanalysis/reference/false_alarm.csv · nomed_false_alarm.csv (저장소에 있음 — 원본 없이 그려진다)
      data/reference/app/agent_summary.csv (시연 주 띠)
출력: reports/figures/fig_adjust_steps.png
실행: python scripts/fig_adjust_steps.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
값이 바뀌어 다시 그려야 할 때만 만든 사람이 새로 올린다.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reanalysis" / "reference"
APP = ROOT / "data" / "reference" / "app" / "agent_summary.csv"
OUT = ROOT / "reports" / "figures" / "fig_adjust_steps.png"

STEPS = ["(0)\n보정 없음", "(1)\n계절형", "(2)\n+ 공통 충격"]
DEMO_DAY = "2025-10-12"

# fig_stay_heatmap.py 와 같은 팔레트를 쓴다 — 발표자료 안에서 색이 따로 놀지 않게
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
BAR, BAR_UP, FAINT = "#3987e5", "#184f95", "#9ec5f4"


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def series(name: str) -> list[int]:
    """false_alarm 꼴 CSV 의 「전체 알림」 세 단계. 첫 열에 이름이 없어 index_col=0 으로 읽는다."""
    d = pd.read_csv(REF / name, index_col=0, encoding="utf-8-sig")
    return [int(v) for v in d["전체 알림"]]


def main() -> None:
    korean_font()
    full, nomed = series("false_alarm.csv"), series("nomed_false_alarm.csv")
    s = pd.read_csv(APP)
    r = s[s["기준일"] == DEMO_DAY].iloc[0]
    demo = [int(r["경보일_보정없음"]), int(r["경보일_계절보정"]), int(r["경보일_공통충격보정"])]

    fig = plt.figure(figsize=(9.6, 6.6), facecolor=SURFACE)
    ax = fig.add_axes((0.055, 0.455, 0.905, 0.40))
    bx = fig.add_axes((0.055, 0.205, 0.905, 0.145))
    x = range(3)

    # ── 위: 6개월 전체. (1)이 (0)보다 높은 것이 이 그림의 요점이라 그 막대만 진하게
    bars = ax.bar(x, full, width=0.46, color=[BAR, BAR_UP, BAR], zorder=3)
    for i, (b, v) in enumerate(zip(bars, full)):
        ax.text(b.get_x() + b.get_width() / 2, v + 4, f"{v}", ha="center", va="bottom",
                fontsize=15, color=INK_2 if i != 1 else INK,
                fontweight="normal" if i != 1 else "bold")
    # 병원·약국 분리 — 단계가 아니라 다른 축이라 막대로 그리지 않고 선으로 겹친다.
    # 막대 위를 지나므로 표식과 글자에 바탕색 테두리를 둘러 읽히게 한다
    ax.plot(x, nomed, color=FAINT, lw=2.2, marker="o", ms=7, zorder=5,
            markeredgecolor=SURFACE, markeredgewidth=1.6)
    for i, v in enumerate(nomed):
        ax.text(i, v + 7, f"{v}", ha="center", va="bottom", fontsize=10, color="#2d6fb8", zorder=6,
                bbox=dict(boxstyle="round,pad=0.18", fc=SURFACE, ec="none", alpha=0.9))

    # (0) → (1) 이 늘어난다는 것을 화살표로 한 번 더
    ax.annotate(f"+{full[1] - full[0]}", xy=(0.79, full[1] + 6), xytext=(0.32, full[1] + 40),
                ha="center", fontsize=11, color=INK,
                arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.2,
                                connectionstyle="arc3,rad=-0.3"))
    ax.text(0.32, full[1] + 56, "한 단계만 켜면 늘어납니다", ha="center", fontsize=10, color=INK_2)

    ax.set_title("6개월 전체 — 헛알림 수", loc="left", fontsize=12.5, color=INK, pad=12)
    ax.set_ylim(0, max(full) + 78)
    # 두 계열 이름은 오른쪽 위에 둔다 — 막대 옆에 붙이면 (2) 막대와 겹친다
    ax.plot([2.33, 2.46], [max(full) + 60] * 2, color=BAR, lw=7, solid_capstyle="butt", zorder=4)
    ax.text(2.50, max(full) + 60, "전 업종", ha="left", va="center", fontsize=9, color=INK_2)
    ax.plot([2.33, 2.46], [max(full) + 36] * 2, color=FAINT, lw=2.2, zorder=4)
    ax.plot([2.395], [max(full) + 36], color=FAINT, marker="o", ms=7, zorder=4,
            markeredgecolor=SURFACE, markeredgewidth=1.6)
    ax.text(2.50, max(full) + 36, "병원·약국 분리\n(단계가 아니라 다른 축)", ha="left", va="center",
            fontsize=9, color="#2d6fb8", linespacing=1.5)

    # ── 아래: 시연 주 한 주. 같은 모양이 나오는 것이 두 번째 주장
    bars2 = bx.bar(x, demo, width=0.46, color=[BAR, BAR_UP, BAR], zorder=3)
    for i, (b, v) in enumerate(zip(bars2, demo)):
        bx.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}", ha="center", va="bottom",
                fontsize=12, color=INK_2 if i != 1 else INK,
                fontweight="normal" if i != 1 else "bold")
    bx.set_title("시연 주 한 주(10/06–10/12, 추석) — 경보일 수  ·  같은 모양입니다",
                 loc="left", fontsize=11, color=INK, pad=10)
    bx.set_ylim(0, max(demo) + 24)

    for a, fs in ((ax, 11), (bx, 11)):
        a.set_xticks(list(x), STEPS, fontsize=fs, color=INK_2, linespacing=1.6)
        a.set_yticks([])
        a.tick_params(length=0)
        a.set_xlim(-0.52, 3.05)
        a.set_facecolor(SURFACE)
        for sp in a.spines.values():
            sp.set_visible(False)
        a.grid(axis="y", color="#ececea", lw=1, zorder=0)
    ax.set_xticklabels([])          # 위 칸은 축 이름을 아래 칸과 겹쳐 쓰지 않는다

    fig.text(0.055, 0.082,
             "보정 3단계는 (0) 없음 → (1) 계절형 → (2) + 같은 도시 30·40대 편차 차감입니다. 병원·약국 분리는 "
             "세 번째 단계가 아니라\n같은 3단계를 대상 업종만 바꿔 다시 잰 다른 축입니다.",
             fontsize=8.5, color=MUTED, linespacing=1.7, va="bottom")
    fig.text(0.055, 0.030,
             "출처: reanalysis/reference/false_alarm.csv · nomed_false_alarm.csv · "
             "data/reference/app/agent_summary.csv(시연 주) · 신한카드 제공 데이터, 2025.7~12",
             fontsize=8.5, color=MUTED)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"저장: {OUT.relative_to(ROOT)}  —  전체 {full} · 병원·약국 분리 {nomed} · 시연 주 {demo}")


if __name__ == "__main__":
    main()
