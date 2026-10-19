"""발표 3 · 6 · 9 · 10장 그림 — 표 셋과 흐름도 하나 (수경 몫 그림 넷).

  3장  fig_face_table.png     지표 정의표 (면 · 묻는 것 · 지표 · 데이터 · 단위 · 가르는 상태)
  6장  fig_state_rules.png    상태 판정 규칙표 (상태 · 신호 · 단위 · 판정 규칙 · 처방)
  9장  fig_contact_steps.png  0~3단계 흐름도 (단계 · 하는 주어 · 비용 · 다음으로 가는 조건)
  10장 fig_agent_loops.png    주기 두 갈래 + 도구 대응표 (면 · 도구 · 하는 일 · 데이터)

데이터를 그리는 그림이 아니라 **글을 그리는 그림**이라 입력 파일이 없다. 칸의 글은 보고서와 기획안에서
그대로 옮겼다 — 3장은 보고서 2.1 표, 6장은 7.3 ③ 판정 · 7.4 자원, 9장은 7.5 표와 기획안 4절 비용 칸,
10장은 7.1 주기 · 7.2 도구 표. 글을 고치면 거기도 본다.

6장 상태 색은 화면 ①(app/balgil_app.py 48행)과 같은 값을 쓴다. 「초록 · 평온」도 화면처럼 회색이다 —
캡처(11장)와 색이 따로 놀지 않게.

출력: reports/figures/fig_face_table.png · fig_state_rules.png · fig_contact_steps.png · fig_agent_loops.png
실행: python scripts/fig_slide_tables.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
글이 바뀌어 다시 그려야 할 때만 만든 사람이 새로 올린다.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures"

# fig_stay_heatmap.py 와 같은 팔레트 — 발표자료 안에서 색이 따로 놀지 않게
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
RULE, HEAD_BG, STRIPE = "#dcdad5", "#eef4fc", "#f5f4f1"
# 화면 ① 상태 색 (app/balgil_app.py 48행)
SERIOUS, CRITICAL, WARNING, CALM = "#ec835a", "#d03b3b", "#fab219", "#c3ccd7"

LH = 0.205  # 10pt 한 줄 높이(인치)
PAD = 0.09  # 칸 안 여백(인치)


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def canvas(w: float, h: float):
    """인치 좌표 캔버스 — (0,0)이 왼쪽 아래, (w,h)가 오른쪽 위."""
    fig = plt.figure(figsize=(w, h), facecolor=SURFACE)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def title(ax, x: float, y: float, text: str, sub: str | None = None) -> None:
    ax.text(x, y, text, fontsize=13, color=INK, fontweight="bold", va="top")
    if sub:
        ax.text(x, y - 0.32, sub, fontsize=9.5, color=INK_2, va="top")


def table(ax, x0: float, y0: float, widths: list[float], header: list[str], rows: list[list[str]], *,
          fs: float = 10, chips: list[str] | None = None, strong: set[tuple[int, int]] = frozenset()) -> float:
    """y0(위)에서 아래로 표를 그리고 바닥 y를 돌려준다. 칸 글은 줄바꿈(\\n)을 미리 넣어 둔다.
    chips: 행마다 첫 칸 앞에 붙일 색. strong: 굵게 쓸 (행, 열) — 첫 열은 늘 굵다."""
    xs = [x0]
    for w in widths:
        xs.append(xs[-1] + w)
    lh = LH * fs / 10

    def line(cells: list[str], y: float, bg: str | None, hdr: bool, chip: str | None, r: int) -> float:
        h = max(c.count("\n") + 1 for c in cells) * lh + 2 * PAD
        if bg:
            ax.add_patch(Rectangle((x0, y - h), xs[-1] - x0, h, color=bg, lw=0, zorder=0))
        for j, c in enumerate(cells):
            tx = xs[j] + PAD
            if chip and j == 0:
                ax.add_patch(FancyBboxPatch((tx, y - PAD - lh * 0.78), 0.13, lh * 0.62,
                                            boxstyle="round,pad=0,rounding_size=0.03", color=chip, lw=0))
                tx += 0.21
            bold = hdr or j == 0 or (r, j) in strong
            ax.text(tx, y - PAD, c, va="top", ha="left", fontsize=fs if not hdr else fs - 0.5,
                    color=INK if (bold and not hdr) else INK_2, fontweight="bold" if bold else "normal",
                    linespacing=1.45)
        ax.plot([x0, xs[-1]], [y - h, y - h], color=RULE if not hdr else INK_2, lw=0.8 if not hdr else 1.0)
        return y - h

    y = line(header, y0, HEAD_BG, True, None, -1)
    for i, r in enumerate(rows):
        y = line(r, y, STRIPE if i % 2 else None, False, chips[i] if chips else None, i)
    return y


def source(ax, x: float, y: float, text: str) -> None:
    ax.text(x, y, text, fontsize=8, color=MUTED, va="bottom")


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    print(f"저장: {(OUT / name).relative_to(ROOT)}")


# ── 3장 지표 정의표 ────────────────────────────────────────────────
def face_table() -> None:
    fig, ax = canvas(9.6, 5.4)
    title(ax, 0.3, 5.15, "발길은 네 면으로 잽니다 — 면마다 답할 수 있는 데이터가 하나씩",
          "양 · 질은 「얼마나 좁은가」, 연속성은 「갑자기 멈췄는가」, 터전은 「닿을 곳이 있는가」를 답합니다")
    rows = [
        ["양", "발길이 몇 곳에 닿는가", "유효 발길 수\n업종 비중의 1/Σp²", "카드", "집단", "좁아짐"],
        ["질", "얼굴을 아는 곳인가", "체류 비중\n체류 업종 11개 ÷ 전 업종", "카드", "집단", "좁아짐"],
        ["연속성", "늘 가던 대로 가는가", "7일 창의 리듬 이탈\n보정 뒤 평소 흔들림의 3배 밖", "카드 일별", "집단", "끊김"],
        ["터전", "닿을 곳이 있는가", "터전점수\n통신 네 지표의 도시 안 순위 평균", "통신\n(상가 · 시설은 나란히)", "동", "터전 없음"],
    ]
    y = table(ax, 0.3, 4.45, [0.95, 1.95, 2.75, 1.65, 0.75, 0.95],
              ["면", "묻는 것", "지표", "데이터", "단위", "가르는 상태"], rows, fs=11,
              strong={(3, 4)})
    ax.text(0.3, y - 0.3, "해상도", fontsize=10, color=INK, fontweight="bold", va="top")
    ax.text(1.0, y - 0.3, "집단 36칸 (시군구 × 성 × 연령대, 90대 포함)  ·  동 47칸 (강남 22 · 춘천 25)", fontsize=10,
            color=INK_2, va="top")
    ax.text(1.0, y - 0.6, "카드 지표는 동에 붙이지 않습니다 — 카드는 가맹점 시군구까지만 내려갑니다. 동은 터전만 봅니다.",
            fontsize=10, color=INK_2, va="top")
    source(ax, 0.3, 0.12, "출처: 신한카드 · SK텔레콤 제공 데이터, 2025.7~12 · 소상공인시장진흥공단 상가정보 · 경로당·도서관 표준데이터. "
           "정의는 보고서 2.1~2.5")
    save(fig, "fig_face_table.png")


# ── 6장 상태 판정 규칙표 ───────────────────────────────────────────
def state_rules() -> None:
    fig, ax = canvas(9.6, 5.6)
    title(ax, 0.3, 5.35, "네 상태는 심각도 순서가 아니라 종류입니다",
          "색은 처방의 종류입니다. 노랑이 둘이라 단위(집단 / 동)를 색 옆에 붙입니다. 끊김이 좁아짐보다 앞섭니다")
    rows = [
        ["좁아짐\n노랑 · 집단", "양 · 질\n(카드 월별)", "집단\n90대 뺀 32칸",
         "나이 · 도시 효과를 덜어 낸\n좁아짐 점수 상위 7칸", "사람 쪽에 역할 · 연결\n프로그램 · 봉사 일감"],
        ["끊김\n주황", "연속성\n체류 · 식사만", "신호는 집단\n대응은 개인",
         "보정 뒤 지난 7일 발길이\n평소 흔들림의 3배 밖", "확인 0~3단계(9장)\n+ 모임 · 1365 봉사"],
        ["끊김\n빨강", "연속성\n장보기 · 병원 · 약국까지", "신호는 집단\n대응은 개인",
         "같은 기준으로 장보기 ·\n병원 · 약국까지 끊김", "확인 0~3단계(9장)\n+ 방문 때 복지서비스"],
        ["터전 없음\n노랑 · 동", "터전점수\n(통신)", "동\n47개",
         "도시 안 터전점수\n하위 20%", "동네 쪽에 올 곳\n찾아가기 · 이동 지원 · 거점"],
        ["정상\n초록", "—", "집단", "위 어디에도 들지 않음", "다음 주에 다시 잽니다"],
    ]
    y = table(ax, 0.3, 4.6, [1.45, 1.85, 1.35, 2.35, 2.0],
              ["상태", "신호", "단위", "판정 규칙", "처방"], rows, fs=10.5,
              chips=[WARNING, SERIOUS, CRITICAL, WARNING, CALM], strong={(3, 2)})
    ax.text(0.3, y - 0.25, "처방이 반대인 두 상태 — 좁아짐은 갈 곳은 있는데 발길이 좁아 사람 쪽에, "
            "터전 없음은 갈 곳 자체가 없어 동네 쪽에 붙입니다.", fontsize=9.5, color=INK_2, va="top")
    ax.text(0.3, y - 0.52, "끊김만 사람에게 갑니다. 좁아짐 상위 7칸의 10 · 20대는 끊김 감시 대상이 아니라 다른 자원으로 갑니다.",
            fontsize=9.5, color=INK_2, va="top")
    source(ax, 0.3, 0.12, "판정 규칙은 보고서 7.3 ③ · 자원은 7.4. 끊김 감시는 60 · 70 · 80대 12집단. "
           "색은 화면 ①과 같습니다")
    save(fig, "fig_state_rules.png")


# ── 9장 0~3단계 흐름도 ─────────────────────────────────────────────
def contact_steps() -> None:
    fig, ax = canvas(9.6, 5.4)
    title(ax, 0.3, 5.15, "싼 수단부터 씁니다 — 본인에게 먼저 묻고, 닿지 않으면 발길이 닿던 곳이 확인합니다")
    steps = [
        ("0", "에이전트", "끊긴 칸으로\n돌봄 명부를 걸러\n3명을 올립니다", "0", "칸에 사람이 없으면\n집단 신호만"),
        ("1", "담당자", "본인에게\n전화합니다", "3분", "닿고 이상 없으면\n끝"),
        ("2", "담당자", "발길이 닿던\n곳에 묻습니다\n(기관명만 밝힘)", "통화 1건", "「요즘도 오세요」면\n끝"),
        ("3", "담당자", "방문합니다\n빨강이면 복지\n서비스 후보를 들고", "1시간+", "도움 필요면\n자원 · 기관 연계"),
    ]
    bw, bh, gap, x0, top = 1.7, 1.45, 0.73, 0.3, 3.9
    for i, (n, who, what, cost, cond) in enumerate(steps):
        x = x0 + i * (bw + gap)
        agent = i == 0
        ax.add_patch(FancyBboxPatch((x, top - bh), bw, bh, boxstyle="round,pad=0,rounding_size=0.08",
                                    facecolor=BLUE[0] if agent else "white", edgecolor=BLUE[3] if agent else INK_2,
                                    lw=1.2))
        ax.text(x + 0.14, top - 0.13, n, fontsize=20, color=BLUE[5] if agent else INK, fontweight="bold", va="top")
        ax.text(x + 0.55, top - 0.24, who, fontsize=10.5, color=BLUE[5] if agent else INK, fontweight="bold",
                va="top")
        ax.text(x + 0.14, top - 0.68, what, fontsize=10, color=INK_2, va="top", linespacing=1.45)
        ax.text(x + bw / 2, top - bh - 0.2, f"비용 {cost}", fontsize=10.5, color=INK, fontweight="bold",
                ha="center", va="top")
        # 아래로 빠지는 조건
        ax.annotate("", xy=(x + bw / 2, 1.5), xytext=(x + bw / 2, top - bh - 0.52),
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1))
        ax.text(x + bw / 2, 1.43, cond, fontsize=9.5, color=INK_2, ha="center", va="top", linespacing=1.4)
        if i < 3:
            label = ["3명", "닿지\n않으면", "그래도\n비면"][i]
            xa, xb = x + bw + 0.03, x + bw + gap - 0.03
            ax.annotate("", xy=(xb, top - bh / 2), xytext=(xa, top - bh / 2),
                        arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1.3))
            ax.text((xa + xb) / 2, top - bh / 2 + 0.1, label, fontsize=8.5, color=INK_2, ha="center", va="bottom",
                    linespacing=1.3)
    # 동시 끊김이면 1단계 앞에 공통 사건 확인
    xl = x0 + (bw + gap)
    ax.add_patch(FancyBboxPatch((xl, top + 0.18), 3 * bw + 2 * gap, 0.5, boxstyle="round,pad=0,rounding_size=0.06",
                                facecolor="none", edgecolor=MUTED, lw=1, linestyle=(0, (4, 3))))
    ax.text(xl + 0.14, top + 0.43, "같은 도시 고령 6집단 중 3개 이상이 함께 끊기면 → 1단계 전에 공통 사건(명절 · 큰비)부터 확인",
            fontsize=9.5, color=INK_2, va="center")
    source(ax, 0.3, 0.12, "2단계 창구는 본인 등록으로만 생깁니다 — 단골 가게 또는 경로당 · 마을회관. "
           "비용은 기획안 4절, 단계는 보고서 7.5")
    save(fig, "fig_contact_steps.png")


# ── 10장 주기 두 갈래 + 도구 대응표 ────────────────────────────────
def agent_loops() -> None:
    fig, ax = canvas(9.6, 7.4)
    title(ax, 0.3, 7.18, "판단은 모델이, 실행은 사람이 합니다 — 도구 이름이 네 면을 그대로 따릅니다")

    def chain(y: float, head: str, sub: str, steps: list[str]) -> None:
        ax.text(0.3, y + 0.1, head, fontsize=11, color=INK, fontweight="bold", va="center")
        ax.text(0.3, y - 0.17, sub, fontsize=8.5, color=MUTED, va="center")
        x, w = 2.1, (9.3 - 2.1 - 0.22 * (len(steps) - 1)) / len(steps)
        for k, s in enumerate(steps):
            ax.add_patch(FancyBboxPatch((x, y - 0.22), w, 0.44, boxstyle="round,pad=0,rounding_size=0.08",
                                        facecolor=BLUE[0], edgecolor="none"))
            ax.text(x + w / 2, y, s, fontsize=9.5, color=INK, ha="center", va="center")
            if k < len(steps) - 1:
                ax.annotate("", xy=(x + w + 0.2, y), xytext=(x + w + 0.02, y),
                            arrowprops=dict(arrowstyle="-|>", color=INK_2, lw=1))
            x += w + 0.22

    chain(6.45, "끊김 루프 · 주 1회", "일요일, 지난 7일 창 · 카드 일별",
          ["연속성 감시", "보정", "판정", "명부 교차", "창구 · 자원", "권고"])
    chain(5.8, "좁아짐 루프 · 월 1회", "카드 월별 · 통신 · 상가 · 시설",
          ["양 · 질 재산출", "터전 갱신", "동 우선순위", "자원 배치 제언"])
    rows = [
        ["양", "measure_breadth", "유효 발길 수 — 같은 도시 · 성 50대와 견줌", "카드"],
        ["질", "measure_quality", "체류 비중 — 같은 도시 · 성 50대와 견줌", "카드"],
        ["양 · 질", "narrow_cells", "좁아짐 점수 상위 7칸 (90대 뺀 32칸 중)", "카드"],
        ["연속성", "detect_break · correct_shock\ncheck_weather", "지난 7일 창의 끊김과 종류 · 보정 단계별 경보\n끊긴 창 안의 궂은 날 꼬리표",
         "카드 일별\n기상청 ASOS"],
        ["터전", "map_ground · ground_alerts", "동의 터전점수 · 순위, 하위 20% 동", "통신 · 상가 · 시설"],
        ["판정", "rate_state", "집단 상태 판정 (빨강 · 주황 · 노랑 · 초록)", "위 도구 전부"],
        ["연결", "match_roster · find_counterpart\ncounterpart_kind · place_candidates\nmatch_resource · draft_outreach\ninquiry_script",
         "끊긴 칸으로 명부 거르기 → 먼저 물을 창구\n(가게 / 경로당 · 마을회관)와 장소 → 자원 후보\n→ 근거 문장 · 문의 문구 (고정 틀)",
         "돌봄 명부 · 장소 표\n복지로 · 1365"],
        ["되먹임", "read_outcomes · log_outcome", "종결 기록 → 다음 주 「이어서 할 것」\n임계값은 자동으로 고치지 않음", "담당자 기록"],
    ]
    y = table(ax, 0.3, 5.25, [0.85, 2.85, 3.85, 1.45], ["면", "도구", "하는 일", "데이터"], rows, fs=9.5)
    ax.text(0.3, y - 0.22, "LLM은 부르지 않습니다 — 문장은 고정 틀에 계산값을 넣습니다. 에이전트는 제안까지, "
            "전화 · 문의 · 방문은 사람이 합니다.", fontsize=9.5, color=INK_2, va="top")
    source(ax, 0.3, 0.1, "도구는 src/balgil/agent.py, 표는 보고서 7.1 · 7.2. 명부 · 장소 표 · 종결 기록은 시연에서 가상입니다")
    save(fig, "fig_agent_loops.png")


def main() -> None:
    korean_font()
    face_table()
    state_rules()
    contact_steps()
    agent_loops()


if __name__ == "__main__":
    main()
