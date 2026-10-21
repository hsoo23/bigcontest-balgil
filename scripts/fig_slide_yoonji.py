"""발표 0 · 1 · 2 · 8 · 14 · 15장 그림 — 윤지 몫 여섯 장을 한 번에 만든다.

수경 님 `fig_slide_tables.py`와 같은 틀이다(글꼴 선택 · 색 상수 · 「PNG는 만든 사람만 커밋」).
칸의 글은 발표자료 슬라이드의 **그림 명세**와 보고서에서 그대로 옮긴다. 새로 만든 숫자는 없다.

  0장 fig_cover.png        발길 한 쌍이 좁아지다 끊기는 선 — 글자 없이 선으로만
  1장 fig_problem_venn.png 경제 지표로 거른 명단 ↔ 발길이 끊긴 사람 (겹치지만 덮지 않음) + 시간 축
  2장 fig_four_faces.png   발길 네 면 도식 — 갈래 끝에 「무엇을 낳는가」와 단위
  8장 fig_model_shap.png   성능표(새 진입 · 경보 · AUC) + 집단 단위 SHAP 막대
 14장 fig_substitute.png   치환표 — 대회 데이터 ↔ 운영 시 대체
 15장 fig_limits.png       한계 여덟 줄 — 같은 크기, 색·아이콘 없이

**1장 두 원에 수를 넣지 않는다.** 「기존 체계 보완율」을 내지 못했으므로(09절 9.1-1) 크기로
양을 말하면 근거 없는 주장이 된다. 겹치지 않는 오른쪽만 글자로 강조한다.

**8장은 AUC 열을 가장 왼쪽에 두지 않는다.** 이 장의 주장은 건수(새 진입 18 / 31)이고 AUC는
기준선이 이미 0.887이라 앞세우면 「당연한 결과」가 된다(05절 5.2). `med`는 상위 6개 밖이지만
「수준만 들어감」을 달아 따로 보인다 — 「병원·약국이 그 자리를 채운다」로 읽히지 않게 하는
자리라 빼면 그 주의가 사라진다(05절 5.3).

**2장은 갈래 굵기로 바뀌는 속도를 말하지 않는다.** 끊김은 하루 · 좁아짐은 달이라는 것은
10장 주기 그림이 맡는다. 여기서는 단위(집단 / 동)를 글자로만 적는다.

입력: reanalysis/reference/model_score.csv · data/reference/app/shap_weekly.csv
      (둘 다 저장소에 있음 — 원본 없이 그려진다)
출력: reports/figures/fig_cover.png · fig_problem_venn.png · fig_four_faces.png ·
      fig_model_shap.png · fig_substitute.png · fig_limits.png
실행: python scripts/fig_slide_yoonji.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
MODEL = ROOT / "reanalysis" / "reference" / "model_score.csv"
SHAP = ROOT / "data" / "reference" / "app" / "shap_weekly.csv"

SURFACE, INK, INK_2, MUTED, FAINT = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#ececea"
BLUE, PALE, GRAY = "#2a78d6", "#cde2fb", "#c3ccd7"
W, HGT = 13.44, 6.72           # 축 좌표 (11.2 × 5.6 인치, dpi 200 → 2240 × 1120)

# 05절 5.3 표의 이름. shap_weekly.csv 의 열 이름 → 발표에 쓰는 말
FEATURE_KO = {"m3": "3주 이동평균", "narrow": "이번 주 좁아짐", "breadth_z": "양 (유효 발길 수)",
              "stay_z": "질 (체류 비중)", "meal": "식사 비중", "evening": "저녁 쏠림",
              "med": "병원·약국 비중", "anon": "익명 비중"}
FEATURES = list(FEATURE_KO)


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def canvas():
    fig = plt.figure(figsize=(11.2, 5.6), facecolor=SURFACE)
    ax = fig.add_axes((0.0, 0.0, 1.0, 1.0)); ax.set_axis_off()
    ax.set_xlim(0, W); ax.set_ylim(0, HGT)
    return fig, ax


def title(ax, text, sub=None) -> None:
    ax.text(0.5, 6.25, text, fontsize=17, fontweight="bold", color=INK, va="center")
    if sub:
        ax.text(0.5, 5.80, sub, fontsize=11, color=MUTED, va="center")


def source(ax, text, y=0.3) -> None:
    ax.text(0.5, y, text, fontsize=8.5, color=MUTED, va="center")


def table(ax, x, y, widths, headers, rows, fs=10.5, row_h=0.62) -> float:
    """머리줄 + 줄무늬 없는 표. 반환값은 표가 끝난 y."""
    xs = np.cumsum([0] + list(widths))[:-1] + x
    ax.add_patch(Rectangle((x - 0.18, y - 0.08), sum(widths) + 0.36, 0.56,
                           facecolor="#eef2f7", edgecolor="none", zorder=1))
    for cx, h in zip(xs, headers):
        ax.text(cx, y + 0.2, h, fontsize=fs, fontweight="bold", color=INK_2, va="center", zorder=3)
    ax.plot([x - 0.18, x + sum(widths) + 0.18], [y - 0.1, y - 0.1], color=INK_2, lw=1.4, zorder=2)
    for i, r in enumerate(rows):
        cy = y - 0.1 - row_h * (i + 0.62)
        if i % 2:
            ax.add_patch(Rectangle((x - 0.18, cy - row_h / 2), sum(widths) + 0.36, row_h,
                                   facecolor="#f4f4f2", edgecolor="none", zorder=1))
        for cx, cell in zip(xs, r):
            bold = cell.startswith("*")
            ax.text(cx, cy, cell.lstrip("*"), fontsize=fs, color=INK if bold else INK_2,
                    fontweight="bold" if bold else "normal", va="center", zorder=3)
    return y - 0.1 - row_h * len(rows)


# ──────────────────────────────────────────────────────────── 0장 표지
def cover() -> None:
    fig, ax = canvas()
    t = np.linspace(0, 1, 600)
    for s, lw in ((1.0, 3.2), (-1.0, 3.2)):           # 발길 한 쌍
        amp = 0.62 * (1 - 0.78 * t)                   # 좁아짐 — 폭이 줄어든다
        y = 4.3 + s * amp * (0.78 + 0.22 * np.cos(t * 11))   # 흔들리되 쌍이 겹치지는 않게
        x = 0.9 + t * 11.6
        keep = x < 9.6                                # 끊김 — 여기서 선이 멎는다
        ax.plot(x[keep], y[keep], color=BLUE if s > 0 else GRAY, lw=lw, solid_capstyle="round", zorder=2)
    ax.plot([10.4, 12.5], [4.3, 4.3], color=FAINT, lw=3.2, ls=(0, (1, 2.6)), solid_capstyle="round", zorder=2)
    ax.plot([9.95, 9.95], [3.25, 5.35], color=INK, lw=2.0, zorder=3)      # 끊긴 자리
    fig.savefig(FIG / "fig_cover.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ──────────────────────────────────────────────────────────── 1장 문제
def problem_venn() -> None:
    fig, ax = canvas()
    title(ax, "기존 제도는 돈으로 거릅니다 — 발길이 끊긴 사람은 명단에 없습니다",
          "두 원의 크기는 양이 아닙니다. 「기존 체계 보완율」은 동 단위 공개 경제 지표를 구하지 못해 내지 않았습니다")
    cl, cr, cy, r = 4.45, 6.75, 3.45, 1.72
    ax.add_patch(Circle((cl, cy), r, facecolor="none", edgecolor=GRAY, lw=2.6, zorder=2))
    ax.add_patch(Circle((cr, cy), r, facecolor=PALE, edgecolor=BLUE, lw=2.6, alpha=0.55, zorder=1))
    ax.add_patch(Circle((cr, cy), r, facecolor="none", edgecolor=BLUE, lw=2.6, zorder=3))
    ax.text(cl - 0.95, cy + 0.15, "경제 지표로\n거른 명단", ha="center", va="center",
            fontsize=12, color=INK_2, linespacing=1.6, zorder=4)
    ax.text(cr + 1.02, cy + 0.15, "발길이\n끊긴 사람", ha="center", va="center",
            fontsize=12.5, fontweight="bold", color=BLUE, linespacing=1.6, zorder=4)
    ax.plot([(cl + cr) / 2, (cl + cr) / 2], [cy + 1.05, cy + 1.42], color=GRAY, lw=1.1, zorder=4)
    ax.text((cl + cr) / 2, cy + 1.58, "겹치는 자리 — 지금 보이는 사람", ha="center", va="center",
            fontsize=10, color=MUTED, zorder=4)
    ax.annotate("", xy=(cr + 1.45, cy + 1.25), xytext=(9.3, 5.05),
                arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.6))
    ax.text(9.45, 5.1, "돈은 있지만 발길이 끊긴 사람", fontsize=11.5, fontweight="bold", color=BLUE, va="center")
    ax.text(9.45, 4.72, "지금은 아무 명단에도 오르지 않습니다", fontsize=10, color=INK_2, va="center")

    ax.plot([0.9, 12.5], [1.35, 1.35], color=FAINT, lw=2.4, zorder=1)     # 시간 축
    ax.plot([2.0], [1.35], marker="|", ms=22, mew=3.4, color=BLUE, zorder=3)
    ax.plot([9.4], [1.35], marker="o", ms=15, mfc=PALE, mec=GRAY, mew=1.8, zorder=3)
    ax.text(2.0, 1.78, "주간 루프 3.0일", ha="center", fontsize=11, fontweight="bold", color=BLUE)
    ax.text(9.4, 1.78, "격월 탐색 31.5일", ha="center", fontsize=11, color=INK_2)
    ax.add_patch(FancyArrowPatch((9.1, 0.95), (2.3, 0.95), arrowstyle="-|>", mutation_scale=16,
                                 lw=1.6, color=INK_2))
    ax.text(5.7, 0.72, "28.5일 빠릅니다", ha="center", fontsize=11, fontweight="bold", color=INK)
    source(ax, "조기성은 실제 끊김 14건 기준(scripts/explore_earliness.py · 최종수치표 6절). "
               "보완율을 못 낸 사실은 15장에 적습니다(보고서 9.1-1).", y=0.22)
    fig.savefig(FIG / "fig_problem_venn.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ──────────────────────────────────────────────────────────── 2장 개념
def four_faces() -> None:
    fig, ax = canvas()
    title(ax, "발길 한 단어가 탐지 · 판단 · 원인 · 연결을 모두 낳습니다",
          "네 면의 단위를 글자로 적습니다 — 양 · 질 · 연속성은 집단, 터전은 동")
    cx, cy = 3.05, 3.05
    ax.add_patch(Circle((cx, cy), 1.12, facecolor=PALE, edgecolor=BLUE, lw=2.4, zorder=3))
    ax.text(cx, cy + 0.12, "발길", ha="center", va="center", fontsize=20, fontweight="bold", color=BLUE, zorder=4)
    ax.text(cx, cy - 0.52, "카드 · 통신", ha="center", va="center", fontsize=9.5, color=INK_2, zorder=4)

    rows = [("양", "몇 곳에 가는가", "유효 발길 수", "집단", "탐지 · 판단"),
            ("질", "얼굴을 아는 곳인가", "체류 비중", "집단", "탐지 · 판단"),
            ("연속성", "늘 가던 대로 가는가", "지난 7일 창", "집단", "원인"),
            ("터전", "닿을 곳이 있는가", "동 단위 공급", "동", "연결")]
    ys = [5.0, 3.95, 2.55, 1.5]
    for (face, ask, how, unit, makes), y in zip(rows, ys):
        ax.add_patch(FancyArrowPatch((cx + 1.2, cy + (y - cy) * 0.33), (5.25, y), arrowstyle="-|>",
                                     mutation_scale=16, lw=1.8, color=GRAY,
                                     connectionstyle="arc3,rad=0.12", zorder=2))
        ax.text(5.45, y + 0.2, f"{face} — {ask}", fontsize=13, fontweight="bold", color=INK, va="center")
        ax.text(5.45, y - 0.22, f"{how} · 단위 {unit}", fontsize=10, color=INK_2, va="center")
        ax.add_patch(FancyBboxPatch((10.75, y - 0.3), 2.2, 0.62, boxstyle="round,pad=0.05,rounding_size=0.1",
                                    facecolor="#ffffff", edgecolor=INK_2, lw=1.1, zorder=3))
        ax.text(11.85, y + 0.01, makes, ha="center", va="center", fontsize=11, color=INK, zorder=4)
    ax.text(11.85, 5.62, "무엇을 낳는가", ha="center", fontsize=10.5, fontweight="bold", color=MUTED)
    source(ax, "고립은 발길이 좁아지고 끊기는 일입니다. 발길을 재면 확인해 줄 사람이 같이 나옵니다 — 보고서 1.2 · 2.1.", y=0.55)
    source(ax, "바뀌는 속도(끊김은 하루 · 좁아짐은 달)는 10장 주기 그림에서 말합니다.", y=0.25)
    fig.savefig(FIG / "fig_four_faces.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ──────────────────────────────────────────────────────────── 8장 성능 + SHAP
def model_shap() -> None:
    fig, ax = canvas()
    m = pd.read_csv(MODEL, encoding="utf-8-sig")
    m = m[m["평가"] == "칸 통째로 빼기"].set_index("모델")
    name = {"기준선(이번 주 그대로)": "기준선 (이번 주 그대로)", "로지스틱": "로지스틱",
            "랜덤포레스트": "랜덤포레스트 (본문 모델)"}
    rows = []
    for k, ko in name.items():
        r = m.loc[k]
        hit = f"{int(r['새진입_잡음'])} / {int(r['새진입'])}"
        rows.append([("*" if k != "기준선(이번 주 그대로)" else "") + ko,
                     "*" + hit, f"{int(r['경보'])}건", f"{r['AUC']:.3f}"])
    title(ax, "모델은 한 주 먼저 잡습니다 — 기준선이 한 건도 못 잡는 칸을 잡습니다",
          "칸 통째로 빼기 · 표본 800(25주 × 32칸) · 새로 들어온 칸 31건은 소표본입니다")
    end = table(ax, 0.6, 5.15, [4.3, 2.5, 1.6, 1.4],
                ["모델", "새 진입을 잡은 수", "경보 수", "AUC"], rows)
    ax.text(0.6, end - 0.14, "기준선은 이번 주 상위를 그대로 쓰므로 새 진입이 정의상 0건입니다. "
                             "대신 경보가 175건에서 202건으로 27건 늘었습니다 — 늘어난 수도 같이 적습니다.",
            fontsize=9.5, color=MUTED, va="top")

    s = pd.read_csv(SHAP, encoding="utf-8-sig")
    imp = s[FEATURES].abs().mean().sort_values(ascending=False)
    top, med = imp.head(6), imp["med"]
    ax.text(0.6, 2.58, "집단 단위 기여도 — 평균 |SHAP| 상위 6개", fontsize=12.5, fontweight="bold", color=INK)
    ax.text(0.6, 2.25, "표본 800 · 32칸 · 새 진입 31건", fontsize=10, color=MUTED)
    bx = fig.add_axes((0.205, 0.065, 0.245, 0.255)); bx.set_facecolor(SURFACE)
    ys = np.arange(len(top))[::-1]
    bx.barh(ys, top.values, height=0.62, color=BLUE, zorder=3)
    bx.barh([-1.35], [med], height=0.62, color=GRAY, zorder=3)
    for y, (k, v) in zip(ys, top.items()):
        bx.text(v + 0.004, y, f"{v:.3f}", va="center", fontsize=9, color=INK_2)
        bx.text(-0.006, y, FEATURE_KO[k], va="center", ha="right", fontsize=9.5, color=INK_2)
    bx.text(med + 0.004, -1.35, f"{med:.3f}", va="center", fontsize=9, color=MUTED)
    bx.text(-0.006, -1.35, "병원·약국 (수준만)", va="center", ha="right", fontsize=9.5, color=MUTED)
    bx.set_xlim(0, max(top) * 1.30); bx.set_ylim(-2.1, len(top) - 0.35)
    bx.set_xticks([]); bx.set_yticks([])
    for sp in bx.spines.values():
        sp.set_visible(False)
    for i, ln in enumerate(["터전 변수는 막대에 없습니다 — 모델 입력 11개가 전부 카드 쪽이라",
                           "동네 쪽은 터전 지수와 C3이 받습니다.",
                           "",
                           "`med`는 수준만 들어가 「병원·약국이 그 자리를 채운다」의 근거로",
                           "쓰지 않습니다 — 그 주장은 집단 안의 시간 변화인데 모델의 `med`는",
                           "32칸 사이의 횡단 수준입니다(05절 5.3)."]):
        ax.text(7.35, 2.60 - i * 0.37, ln, fontsize=9.5, color=MUTED, va="center")
    source(ax, "reanalysis/reference/model_score.csv(기준 환경 윈도우 AMD64) · data/reference/app/shap_weekly.csv "
               "· 최종수치표 1절. Apple 실리콘에서는 랜덤포레스트가 16 / 31 · 경보 200입니다(보고서 10.1).", y=0.22)
    fig.savefig(FIG / "fig_model_shap.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ──────────────────────────────────────────────────────────── 14장 치환표
def substitute() -> None:
    fig, ax = canvas()
    title(ax, "운영으로 옮길 때 새로 계약할 것이 없습니다",
          "대회 데이터를 지자체가 이미 가진 것으로 바꿔 놓습니다 — 네 분류는 업종명이 아니라 성질로 정의돼 있습니다")
    rows = [["신한카드 결제", "*지역사랑상품권 · 지역화폐 결제", "★ 지자체 직접 보유", "일별"],
            ["SK 유동인구", "통계청 생활인구 · SGIS 계열", "공개", "월 · 분기"],
            ["—", "*지자체 돌봄 명부", "★ 지자체 직접 보유", "상시"],
            ["행안부 1인세대", "동일 (이미 쓰고 있습니다)", "공개", "매월"],
            ["복지로 · 1365", "동일 (이미 쓰고 있습니다)", "공개 API", "상시"]]
    end = table(ax, 0.6, 5.15, [3.5, 4.6, 3.0, 1.4],
                ["대회 데이터", "운영 시 대체", "보유 주체", "갱신"], rows, row_h=0.62)
    ax.text(0.6, end - 0.30, "★ 두 줄은 지자체가 이미 들고 있는 자료입니다 — 새 계약도 새 수집도 없습니다.",
            fontsize=11, fontweight="bold", color=INK, va="top")
    ax.text(0.6, end - 0.74, "가장 약한 고리는 카드입니다. 업종 코드 체계가 달라도 우리 분류가 "
                             "**체류 · 식사 · 익명 · 병원·약국**이라는 **성질**로 정의돼 있어 다시 묶을 수 있습니다(보고서 9.3).".replace("**", ""),
            fontsize=10, color=INK_2, va="top")
    ax.text(0.6, end - 1.12, "다만 가맹 구성이 달라(대형 할인점이 빠지고 동네 슈퍼가 늘어납니다) "
                             "비중은 쓰되 절대 건수는 지역 간 비교에 쓰지 않습니다.",
            fontsize=10, color=INK_2, va="top")
    source(ax, "보고서 9.3 치환표. 퍼널 수치는 내지 않습니다 — 재현할 코드가 없고(#14), "
               "가상 명부 41명으로는 절감률을 대신하지 못합니다.", y=0.25)
    fig.savefig(FIG / "fig_substitute.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


# ──────────────────────────────────────────────────────────── 15장 한계
def limits() -> None:
    fig, ax = canvas()
    title(ax, "약한 곳을 먼저 말합니다",
          "여덟 줄을 같은 크기로 둡니다 — 강조하면 「덜 중요한 한계」가 생깁니다")
    rows = [("기간이 6개월", "계절 한 바퀴를 못 봤습니다", "계절 보정으로 일부 상쇄 · 연 단위 재검증 필요"),
            ("지역이 둘", "일반화 근거가 약합니다", "설계 자원으로 썼습니다 — 가게가 없는 동 ↔ 경로당"),
            ("「기존 체계 보완율」", "동 단위 공개 경제 지표를 못 구했습니다", "못 냈다고 적고 세 지표 중 둘로 말합니다"),
            ("창구 기준값 3", "관측이 아니라 판단입니다", "2~5배 민감도를 재 세 면으로 좁혀 말합니다"),
            ("카드 표본 치우침", "60대 이상이 거주 인구의 0.51~0.64배", "집단 안의 비중으로만 말합니다"),
            ("시연은 사후 분석 값", "기준일 뒤 데이터가 최대 80일 섞입니다", "재 보니 시연 주 빨강 9 → 8 · 10/01 주황 1 → 3"),
            ("소표본", "새로 들어온 칸이 31건입니다", "성능 수치에 표본 수를 같은 줄에 적습니다"),
            ("확인 창구가 동마다 다름", "가게가 없는 동에는 단골이 없습니다", "2단계 상대방을 「가게 또는 경로당」으로 둡니다")]
    y = 5.15
    for head, what, how in rows:
        ax.text(0.6, y, head, fontsize=11.5, fontweight="bold", color=INK, va="center")
        ax.text(4.15, y, what, fontsize=10.5, color=INK_2, va="center")
        ax.text(7.75, y, "→", fontsize=10.5, color=MUTED, va="center")
        ax.text(8.2, y, how, fontsize=10.5, color=INK_2, va="center")
        y -= 0.56
    ax.plot([0.6, 12.9], [y + 0.22, y + 0.22], color=FAINT, lw=1.6)
    ax.text(0.6, y - 0.18, "대리 라벨은 이 그림에 넣지 않습니다 — 한계가 아니라 폐기 결정이고 8장에서 근거로 씁니다.",
            fontsize=10, color=INK_2, va="center")
    source(ax, "못 낸 것을 적는 편이 안 적고 넘어가는 것보다 셉니다 — 규정이 「참가자의 직접적인 검증 및 설명」을 요구합니다. "
               "보고서 10절 10.1.", y=0.3)
    fig.savefig(FIG / "fig_limits.png", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    korean_font()
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (cover, problem_venn, four_faces, model_shap, substitute, limits):
        f()
        print(f"저장: reports/figures — {f.__name__}")


if __name__ == "__main__":
    main()
