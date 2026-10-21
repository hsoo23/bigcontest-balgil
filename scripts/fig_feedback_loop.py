"""발표 12장 그림 — 종결 되먹임 루프 (신호 → 확인 → 종결 기록 → 임계값 조정 → 신호).

**종결 기록에서 임계값으로 가는 화살표가 이 그림의 주인공이다.** 지속 활용성의 답이
「쓸수록 맞아지는 구조」이고, 그 구조가 실제로 도는 자리가 거기다(09절 9.3).

**「설계」 표시는 그 화살표에만 붙인다.** `log_outcome`은 이미 구현돼 있고 칸별 종결 기록을
낸다(src/balgil/agent.py 603행). 설계인 쪽은 **임계값을 사람이 조정하는 부분**이다 —
`log_outcome` 독스트링이 「임계값을 자동으로 바꾸지는 않는다 … 실제 기록이 쌓인 뒤 사람이
정한다」로 적고 있다(보고서 7.5 · 10.1, #103 6번 · #104 수경 지적).

**집단 종결을 쓰지 않는 이유를 옆에 작게 적는다.** 6개월 끊김 14건이 전부 「함께 복귀」로
끝나 반례가 0건이다. 집단 단위로는 가를 것이 없어서 종결을 개인 단위 규칙으로만 둔다
(최종수치표 4절 · 05절 5.5).

단계 이름과 결과 세 가지는 코드에서 그대로 가져온다 — agent.OUTCOME_STEPS ·
OUTCOME_RESULTS. 글을 고치면 코드와 어긋나므로 import 해서 쓴다.

입력: src/balgil/agent.py (상수만. 데이터 파일을 읽지 않아 원본 없이 그려진다)
출력: reports/figures/fig_feedback_loop.png
실행: python scripts/fig_feedback_loop.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from balgil.agent import OUTCOME_RESULTS, OUTCOME_STEPS  # noqa: E402

OUT = ROOT / "reports" / "figures" / "fig_feedback_loop.png"

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
AGENT, AGENT_EDGE, LINE, FAINT = "#cde2fb", "#2a78d6", "#52514e", "#ececea"

BREAKS, COUNTER = 14, 0          # 최종수치표 4절 — 끊김 14건, 함께 복귀 반례 0건
W, H = 3.5, 1.5                  # 상자 크기


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def box(ax, cx, cy, head, lines, agent=False) -> None:
    """네모 하나. 에이전트가 하는 칸만 파랗게 — 사람이 하는 칸과 가른다."""
    ax.add_patch(FancyBboxPatch((cx - W / 2, cy - H / 2), W, H, boxstyle="round,pad=0.07,rounding_size=0.12",
                                facecolor=AGENT if agent else "#ffffff",
                                edgecolor=AGENT_EDGE if agent else INK_2, lw=1.8 if agent else 1.2, zorder=3))
    ax.text(cx, cy + H / 2 - 0.36, head, ha="center", va="center", fontsize=13.5, fontweight="bold",
            color=AGENT_EDGE if agent else INK, zorder=4)
    for i, ln in enumerate(lines):
        ax.text(cx, cy + H / 2 - 0.72 - i * 0.33, ln, ha="center", va="center",
                fontsize=10, color=INK_2, zorder=4)


def arrow(ax, p0, p1, lw, color=LINE) -> None:
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=18 + lw * 4,
                                 lw=lw, color=color, shrinkA=0, shrinkB=0, zorder=2))


def main() -> None:
    korean_font()
    fig = plt.figure(figsize=(11.2, 5.6), facecolor=SURFACE)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0)); ax.set_axis_off()
    ax.set_xlim(0, 13.44); ax.set_ylim(0, 6.72)

    ax.text(0.5, 6.25, "쓸수록 맞아지는 구조 — 종결 기록이 다음 주 신호로 돌아옵니다",
            fontsize=17, fontweight="bold", color=INK, va="center")
    ax.text(0.5, 5.80, "종결은 개인 단위 규칙으로만 둡니다. 판단은 에이전트가, 확인과 조정은 사람이 합니다",
            fontsize=11, color=MUTED, va="center")

    lx, rx, ty, by = 2.65, 7.35, 4.35, 1.95      # 네 상자의 중심
    box(ax, lx, ty, "① 신호", ["끊긴 칸 · 좁아짐 칸을 올립니다", "집단(시군구 × 성 × 연령) 단위"], agent=True)
    box(ax, rx, ty, "② 확인", [f"{OUTCOME_STEPS[0][0]}~{OUTCOME_STEPS[-1][0]}단계 — "
                               f"{' → '.join(s[2:] for s in OUTCOME_STEPS)}", "여기서부터 사람 단위"])
    box(ax, rx, by, "③ 종결 기록", [" · ".join(OUTCOME_RESULTS), "`log_outcome` — 이미 구현돼 있습니다"])
    box(ax, lx, by, "④ 임계값 조정", ["「이상 없음」이 쌓인 칸은 경보가 헐겁습니다",
                                  "자동으로 바꾸지 않습니다 — 사람이 다시 잡습니다"])

    arrow(ax, (lx + W / 2 + 0.1, ty), (rx - W / 2 - 0.1, ty), 1.6)
    arrow(ax, (rx, ty - H / 2 - 0.1), (rx, by + H / 2 + 0.1), 1.6)
    arrow(ax, (rx - W / 2 - 0.1, by), (lx + W / 2 + 0.1, by), 4.2, INK)   # 되먹임 — 가장 굵게
    arrow(ax, (lx, by + H / 2 + 0.1), (lx, ty - H / 2 - 0.1), 1.6)

    ax.text((lx + rx) / 2, ty + 0.32, "명부 교차", ha="center", fontsize=10, color=MUTED)
    ax.text(rx + 0.22, (ty + by) / 2, "싼 수단부터\n(9장)", ha="left", va="center", fontsize=10, color=MUTED)
    ax.text(lx - 0.22, (ty + by) / 2, "다음 주\n신호로", ha="right", va="center", fontsize=10, color=MUTED)

    # 되먹임 화살표에만 「설계」 — log_outcome(③)이 아니라 이 화살표가 설계다
    ax.add_patch(FancyBboxPatch(((lx + rx) / 2 - 0.46, by + 0.26), 0.92, 0.46,
                                boxstyle="round,pad=0.04,rounding_size=0.1",
                                facecolor=SURFACE, edgecolor=MUTED, lw=1.0, ls=(0, (4, 2)), zorder=4))
    ax.text((lx + rx) / 2, by + 0.49, "설계", ha="center", va="center",
            fontsize=10.5, color=INK_2, zorder=5)

    ax.text(9.55, 4.62, "집단 종결은 쓰지 않습니다", fontsize=12.5, fontweight="bold", color=INK, va="center")
    for i, ln in enumerate([
            f"6개월 끊김 {BREAKS}건이 **전부** 「함께 복귀」로",
            f"끝났습니다 — 필수만 돌아오고 대면은",
            f"안 돌아온 반례가 {COUNTER}건입니다.",
            "",
            "집단 단위로는 가를 것이 없어서,",
            "종결은 사람마다 따로 적습니다."]):
        ax.text(9.55, 4.18 - i * 0.37, ln.replace("**", ""), fontsize=10.5, color=INK_2, va="center")

    ax.plot([9.25, 9.25], [1.95, 4.80], color=FAINT, lw=2, zorder=1)

    ax.text(0.5, 0.52, "도구는 src/balgil/agent.py(`log_outcome` · `read_outcomes`), 단계와 결과 이름은 그 파일 상수. "
                       "글은 보고서 7.5 · 9.3 · 10.1, 끊김 14건은 최종수치표 4절.",
            fontsize=8.5, color=MUTED, va="center")
    ax.text(0.5, 0.22, "시연의 종결 기록은 가상 명부(41명)에서 나온 가상 값입니다 — 성능 수치로 쓰지 않습니다.",
            fontsize=8.5, color=MUTED, va="center")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"저장: {OUT.relative_to(ROOT)}  —  단계 {OUTCOME_STEPS} · 결과 {OUTCOME_RESULTS}")


if __name__ == "__main__":
    main()
