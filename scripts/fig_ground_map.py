"""발표 5장 그림 — 47개 동 지도, 춘천 · 강남 두 장 나란히.

**색은 화면 ③ 「대응 (공급 × 필요)」 그대로다.** 공급은 통신 터전순위 하위 절반, 필요는 고령 1인세대가
도시 중앙값 이상이다(build_priority.py). 색 넷과 그 순서·값은 app/balgil_app.py QUAD 와 같다 —
화면 캡처(11장)와 이 그림이 같은 동을 같은 색으로 칠해야 심사위원이 둘을 맞대 볼 수 있다.

**칠하는 것은 동 단위 공급뿐이다.** 카드 지표(양·질·끊김)는 시군구까지라 동에 칠하지 않는다
(발표 5장 주석). 점은 경로당·마을회관(속 빈 점)과 도서관(채운 점)이고, 대응 색과 겹치지 않게 먹색이다.

**글자는 고른 동에만 붙인다.** 「1순위 · 거점 배치」 동과, 5장 본문이 사례로 드는 북산면이다.
색만으로 말하지 않도록 범례에 칸 이름과 정의를 함께 적는다.

입력: data/reference/app/dong_map.geojson · facilities.csv · data/reference/dong_priority.csv
      (전부 저장소에 있음 — 원본 없이, geopandas 없이 그려진다)
출력: reports/figures/fig_ground_map.png
실행: python scripts/fig_ground_map.py

PNG는 바이트로는 재현되지 않는다 — PC마다 글꼴 렌더링이 달라 픽셀 몇백 개가 다르다.
그래서 **한 사람이 만들어 커밋하고, 다른 PC에서는 다시 만들어 커밋하지 않는다**(#72).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Polygon  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "reference" / "app" / "dong_map.geojson"
FAC = ROOT / "data" / "reference" / "app" / "facilities.csv"
PRI = ROOT / "data" / "reference" / "dong_priority.csv"
OUT = ROOT / "reports" / "figures" / "fig_ground_map.png"

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
# app/balgil_app.py QUAD 와 같은 값·순서 (화면에서 --pairs all 검증을 통과한 세 색 + 회색 「유지」)
QUAD = {
    "1순위": ("#2a78d6", "1순위 · 거점 배치", "공급 부족 · 필요 큼"),
    "형평": ("#eb6834", "형평 · 찾아가기", "공급 부족 · 사람 적음"),
    "연결": ("#1baf7a", "연결 · 있는 곳에 붙이기", "공급 있음 · 필요 큼"),
    "유지": ("#cfd6df", "유지", "공급 있음 · 사람 적음"),
}
CASE = {"북산면"}       # 5장 본문이 사례로 드는 동 — 1순위가 아니어도 이름을 붙인다
# 이웃한 작은 동은 무게중심에 그대로 두면 글자가 겹친다 — 점(pt) 단위로 비켜 놓는다
NUDGE = {"역삼1동": (-16, 9), "역삼2동": (14, -10)}
CITIES = [("춘천", "강원 춘천시"), ("강남", "서울 강남구")]


def korean_font() -> None:
    have = {f.name for f in fm.fontManager.ttflist}
    plt.rcParams["font.family"] = next(
        (n for n in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if n in have),
        "sans-serif")
    plt.rcParams["axes.unicode_minus"] = False


def rings(geom: dict) -> list[list[list[float]]]:
    """Polygon · MultiPolygon 의 바깥 고리만 꺼낸다(구멍은 이 경계에서 그릴 만큼 크지 않다)."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    return [poly[0] for poly in geom["coordinates"]]


def centroid(ring: list[list[float]]) -> tuple[float, float]:
    """넓이 가중 무게중심(신발끈 공식). 꼭짓점 평균은 해안선처럼 점이 몰린 쪽으로 끌린다."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    return cx / (3 * a), cy / (3 * a)


def area(ring: list[list[float]]) -> float:
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))) / 2


def draw_city(ax, feats: list[dict], fac: pd.DataFrame, pri: pd.DataFrame) -> str:
    xs, ys = [], []
    for f in feats:
        q = pri.loc[f["properties"]["ADM_CD"], "사분면"]
        for r in rings(f["geometry"]):
            ax.add_patch(Polygon(r, closed=True, facecolor=QUAD[q][0], edgecolor=SURFACE, lw=1.4, zorder=1))
            xs += [p[0] for p in r]; ys += [p[1] for p in r]

    # 경로당은 많아서 속 빈 점(지도를 덮지 않게), 도서관은 적어서 채운 점
    s = fac[fac["시설종류"] == "경로당"]
    ax.scatter(s["경도"], s["위도"], s=9, facecolor="#ffffff", edgecolor=INK, lw=0.6, zorder=3)
    s = fac[fac["시설종류"] == "도서관"]
    ax.scatter(s["경도"], s["위도"], s=26, facecolor=INK, edgecolor="#ffffff", lw=0.9, zorder=4)

    for f in feats:
        nm, cd = f["properties"]["ADM_NM"], f["properties"]["ADM_CD"]
        if pri.loc[cd, "사분면"] != "1순위" and nm not in CASE:
            continue
        x, y = centroid(max(rings(f["geometry"]), key=area))
        ax.annotate(nm, (x, y), xytext=NUDGE.get(nm, (0, 0)), textcoords="offset points", ha="center",
                    va="center", fontsize=10.5, color=INK, fontweight="bold", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.22", fc=SURFACE, ec="none", alpha=0.88))

    # 경위도를 그대로 쓰면 동서가 늘어난다 — 위도에 맞춰 가로 비를 줄인다
    ax.set_xlim(min(xs), max(xs)); ax.set_ylim(min(ys), max(ys))
    ax.set_aspect(1 / math.cos(math.radians((min(ys) + max(ys)) / 2)))
    ax.set_axis_off()
    n = pri.loc[[f["properties"]["ADM_CD"] for f in feats], "사분면"].value_counts()
    return " · ".join(f"{QUAD[k][1].split(' · ')[0]} {n.get(k, 0)}곳" for k in QUAD)


def main() -> None:
    korean_font()
    geo = json.load(open(GEO, encoding="utf-8"))["features"]
    fac = pd.read_csv(FAC, encoding="utf-8-sig")
    pri = pd.read_csv(PRI, encoding="utf-8-sig", dtype={"ADM_CD": str})
    pri["사분면"] = pri["대응"].str.split(" — ").str[0]
    pri = pri.set_index("ADM_CD")
    assert set(pri["사분면"]) <= set(QUAD), set(pri["사분면"]) - set(QUAD)

    fig = plt.figure(figsize=(12.8, 7.2), facecolor=SURFACE)
    boxes = [(0.02, 0.12, 0.55, 0.64), (0.60, 0.12, 0.38, 0.64)]   # 춘천이 넓어 왼쪽을 크게
    panels = []
    for (city, sgg), box in zip(CITIES, boxes):
        feats = [f for f in geo if f["properties"]["도시"] == city]
        ax = fig.add_axes(box)
        panels.append((ax, f"{city} {len(feats)}개 동", draw_city(ax, feats, fac[fac["SGG_NM"] == sgg], pri)))

    # 가로세로 비를 맞추면 두 지도의 실제 높이가 달라진다 — 제목은 축 대신 그림 좌표에서 같은 줄에 둔다
    for ax, _, _ in panels:
        ax.apply_aspect()
    top = max(ax.get_position().y1 for ax, _, _ in panels)
    for ax, title, counts in panels:
        x0 = ax.get_position().x0
        fig.text(x0, top + 0.055, title, fontsize=15, color=INK, fontweight="bold", va="bottom")
        fig.text(x0, top + 0.015, counts, fontsize=10.5, color=INK_2, va="bottom")

    fig.text(0.02, 0.955, "발길 닿을 곳은 동네마다 다릅니다 — 공급 × 필요로 자원을 둘 동을 고릅니다",
             fontsize=17, color=INK, fontweight="bold", va="top")
    handles = [Patch(facecolor=c, edgecolor="none", label=f"{name}  ({rule})") for c, name, rule in QUAD.values()]
    handles += [Line2D([], [], ls="", marker="o", ms=5, mfc="#ffffff", mec=INK, mew=0.8, label="경로당·마을회관"),
                Line2D([], [], ls="", marker="o", ms=7, mfc=INK, mec="#ffffff", label="도서관")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.02, 0.005), ncol=3, frameon=False,
               fontsize=10.5, handlelength=1.4, columnspacing=1.8, labelcolor=INK_2)
    fig.text(0.02, 0.905, "공급 부족 = 도시 안 통신 터전 약한 절반 · 필요 큼 = 고령 1인세대 수가 도시 중앙값 이상.  "
             "색은 동 단위 값(공급 × 필요)입니다 — 카드 지표(양·질·끊김)는 시군구까지라 동에 칠하지 않습니다",
             fontsize=10, color=MUTED, va="top")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor=SURFACE)
    print(f"저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
