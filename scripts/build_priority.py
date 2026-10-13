"""동 우선순위표와 도달 효율 (C5) → data/reference/dong_priority.csv, reach_efficiency.csv (git에 올린다).

우선순위는 두 축으로 정한다.
  공급  터전이 약한가 — 통신 터전순위가 도시 안 하위 절반(강남 11, 춘천 12)
  필요  닿아야 할 사람이 많은가 — 행안부 2025-12 고령(60세 이상) 1인세대 수

기획안 정의("터전 하위 동에 배치")만 쓰면 춘천에서는 인구가 적은 면 지역이 뽑혀
같은 수의 동에 배치했을 때 무작위보다 적게 닿는다(아래 reach_efficiency 「터전 하위」 줄).
그래서 터전 하위 절반 안에서 고령 1인세대가 많은 순으로 우선순위를 매긴다.
가게도 사람도 적은 면 지역은 효율이 아니라 형평(닿을 곳이 없다)의 근거로 따로 표시한다.

도달 효율 = 우선순위 상위 k개 동의 고령 1인세대 수 합 ÷ 무작위 k개 동의 기댓값(k × 도시 평균)
  1이면 무작위와 같다. 「1인세대 많은 순」은 터전을 보지 않을 때의 상한이다.

2단계 창구: 체류형 점포가 경로당·마을회관의 3배가 안 되면 경로당 창구 후보로 표시한다.
  (#29 agent.py counterpart_kind의 초안 기준과 같다. 실제 창구는 집단의 업종으로 agent가 고른다)

선행: build_ground.py
실행: python scripts/build_priority.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402

REF = ROOT / "data" / "reference"
SHOP_PER_CENTER = 3  # agent.py(#29) SHOP_PER_CENTER와 같은 초안 값. 10/17 확정 뒤 함께 바꾼다
KS = (3, 5)

ACTION = {  # (공급 부족, 필요 큼) → 무엇을 하는가 (기획안 6절)
    (True, True): "1순위 — 거점 배치·정기 프로그램 (닿을 곳을 만들고 사람이 많다)",
    (True, False): "형평 — 찾아가는 형태·이동 지원 (닿을 곳도 사람도 적다, 연간 예산 제언)",
    (False, True): "연결 — 있는 가게·시설에 모임·봉사를 붙인다",
    (False, False): "유지",
}


def build() -> pd.DataFrame:
    g = pd.read_csv(REF / "dong_ground.csv", dtype={"ADM_CD": str})
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    old = hh[hh["연령대"].isin(["60대", "70대이상"])].groupby("ADM_CD")[["일인세대수", "인구수"]].sum()
    g = g.merge(old.rename(columns={"일인세대수": "고령1인세대수"})["고령1인세대수"], left_on="ADM_CD", right_index=True)
    assert g["고령1인세대수"].notna().all() and len(g) == 47
    g["고령1인세대율"] = (g["고령1인세대수"] / g["인구_60세이상"]).round(3)

    n = g.groupby("도시")["ADM_CD"].transform("size")
    g["공급부족"] = g["터전순위_통신"] <= n // 2
    med = g.groupby("도시")["고령1인세대수"].transform("median")
    g["필요큼"] = g["고령1인세대수"] >= med
    g["대응"] = [ACTION[(a, b)] for a, b in zip(g["공급부족"], g["필요큼"])]
    # 우선순위: 공급 부족 동을 먼저, 그 안에서 고령 1인세대가 많은 순
    g = g.sort_values(["도시", "공급부족", "고령1인세대수"], ascending=[True, False, False])
    g["우선순위"] = g.groupby("도시").cumcount() + 1
    g["경로당창구후보"] = g["체류형점포수"] < SHOP_PER_CENTER * g["경로당수"]
    cols = ["도시", "SGG_NM", "ADM_CD", "ADM_NM", "우선순위", "대응", "공급부족", "필요큼", "터전순위_통신",
            "고령1인세대수", "고령1인세대율", "인구_60세이상", "체류형점포수", "경로당수", "마을회관수", "도서관수", "경로당창구후보"]
    return g[cols].reset_index(drop=True)


def reach(g: pd.DataFrame) -> pd.DataFrame:
    rules = {
        "터전 하위 (기획안 정의)": lambda x: x.nsmallest(K, "터전순위_통신"),
        "우선순위 (터전 하위 절반 ∩ 1인세대 많은 순)": lambda x: x.nsmallest(K, "우선순위"),
        "1인세대 많은 순 (터전 무시, 상한)": lambda x: x.nlargest(K, "고령1인세대수"),
    }
    rows = []
    global K
    for city, x in g.groupby("도시", sort=False):
        for K in KS:
            expect = K * x["고령1인세대수"].mean()
            for name, pick in rules.items():
                sel = pick(x)
                rows.append((city, K, name, int(sel["고령1인세대수"].sum()), round(expect), round(sel["고령1인세대수"].sum() / expect, 2),
                             ", ".join(sel["ADM_NM"])))
    return pd.DataFrame(rows, columns=["도시", "k", "규칙", "도달(고령 1인세대)", "무작위 기댓값", "도달 효율", "동"])


def main() -> None:
    g = build()
    r = reach(g)
    print("■ 도달 효율 (무작위 = 1)")
    print(r.drop(columns="동").to_string(index=False))
    print("\n■ 도시별 우선순위 상위 5")
    for city, x in g.groupby("도시", sort=False):
        print(x.head(5)[["ADM_NM", "터전순위_통신", "고령1인세대수", "고령1인세대율", "경로당창구후보"]].to_string(index=False))
    print("\n■ 사분면 동 수")
    print(g.groupby(["도시", "대응"]).size().to_string())
    g.to_csv(REF / "dong_priority.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    r.to_csv(REF / "reach_efficiency.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    print("\n저장: data/reference/dong_priority.csv, reach_efficiency.csv")


if __name__ == "__main__":
    main()
