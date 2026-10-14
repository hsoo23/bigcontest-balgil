"""47개 동의 터전 표를 만든다 (C3) → data/reference/dong_ground.csv (git에 올린다).

터전은 "그 동에 닿을 곳이 있는가"를 보는 공급 지표다(#6 결론). 세 재료를 한 줄에 놓되 더하지 않는다.
  통신   터전점수_통신·순위 (수경 A4 동 패널). 낮을수록 터전이 약하다
  상가   60세+ 천 명당 체류형 점포 (C2, features.is_stay_store)
  시설   60세+ 천 명당 경로당·마을회관, 도서관 (C3, build_facility.py)
상가와 시설은 춘천에서 방향이 반대라(가게가 적은 면 지역에 경로당이 많다) 한 지수로 더하면 서로 지운다.
그래서 지수를 새로 만들지 않고, 같은 동을 세 재료로 나란히 본다. 분모는 행안부 2025-12 주민 60세 이상.

함께 출력하는 검증 (#6)
  통신 터전점수 × 상가·시설 Spearman, 도시별. 60대 비중 항목을 뺀 점수로도 다시 잰다
  (강남의 상가 상관은 그 항목에서 나온다 — 수경 확인)

선행: build_dong_panel.py → build_spatial.py(store_adm) → build_external.py(행안부) → build_facility.py
실행: python scripts/build_ground.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402
from balgil.features import is_stay_store  # noqa: E402
from build_dong_panel import RANK_BY  # noqa: E402

OUT = ROOT / "data" / "reference" / "dong_ground.csv"
# A4 터전점수 항목에서 60대 비중만 뺀다 (A4 항목이 바뀌면 같이 따라간다)
RANK_NO_SHARE = [(c, asc) for c, asc in RANK_BY if c != "60대이상_비중"]
assert len(RANK_NO_SHARE) == len(RANK_BY) - 1


def build() -> pd.DataFrame:
    panel = pd.read_parquet(PROCESSED_DIR / "features_dong.parquet")
    for col, asc in RANK_NO_SHARE:
        panel[f"R_{col}"] = panel.groupby("도시")[col].rank(ascending=asc)
    panel["터전점수_통신_비중제외"] = panel[[f"R_{c}" for c, _ in RANK_NO_SHARE]].mean(axis=1)

    store = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet")
    stay = store[is_stay_store(store)].groupby("ADM_CD").size().rename("체류형점포수")
    fac = pd.read_parquet(PROCESSED_DIR / "fac_dong.parquet")[["ADM_CD", "경로당수", "마을회관수", "도서관수"]]
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    pop = hh[hh["연령대"].isin(["60대", "70대이상"])].groupby("ADM_CD")["인구수"].sum().rename("인구_60세이상")

    g = (
        panel[["도시", "SGG_NM", "ADM_CD", "ADM_NM", "터전점수_통신", "터전순위_통신", "터전점수_통신_비중제외"]]
        .merge(stay, on="ADM_CD", how="left")
        .merge(fac, on="ADM_CD", how="left")
        .merge(pop, on="ADM_CD", how="left")
    )
    g["체류형점포수"] = g["체류형점포수"].fillna(0).astype(int)
    assert g["인구_60세이상"].notna().all(), "행안부 60세 이상 인구가 없는 동이 있습니다"
    per = g["인구_60세이상"] / 1000
    g["체류형점포_천명당"] = (g["체류형점포수"] / per).round(2)
    g["경로당_천명당"] = (g["경로당수"] / per).round(2)
    g["도서관_천명당"] = (g["도서관수"] / per).round(2)
    # 도시 안 순위: 1 = 가장 적다(약하다). 통신 터전순위와 같은 방향
    for c in ["체류형점포_천명당", "경로당_천명당"]:
        g[c.replace("_천명당", "_순위")] = g.groupby("도시")[c].rank(method="first").astype(int)
    g["터전점수_통신_비중제외"] = g["터전점수_통신_비중제외"].round(3)
    g["터전점수_통신"] = g["터전점수_통신"].round(3)
    return g.sort_values(["도시", "터전순위_통신"]).reset_index(drop=True)


def check(g: pd.DataFrame) -> None:
    print("■ 통신 터전점수 × 60세+ 천 명당 공급, Spearman (도시별)")
    rows = []
    for city, x in g.groupby("도시", sort=False):
        for score in ["터전점수_통신", "터전점수_통신_비중제외"]:
            for supply in ["체류형점포_천명당", "경로당_천명당", "도서관_천명당"]:
                r, p = spearmanr(x[score], x[supply])
                rows.append((city, len(x), score, supply, round(r, 2), round(p, 3)))
        r, p = spearmanr(x["체류형점포_천명당"], x["경로당_천명당"])
        rows.append((city, len(x), "체류형점포_천명당", "경로당_천명당", round(r, 2), round(p, 3)))
    print(pd.DataFrame(rows, columns=["도시", "n", "x", "y", "rho", "p"]).to_string(index=False))

    print("\n■ 도시별 하위 3개 동 (통신 / 상가 / 경로당)")
    for city, x in g.groupby("도시", sort=False):
        low = lambda c: ", ".join(x.nsmallest(3, c)["ADM_NM"])  # noqa: E731
        print(f"  {city}  통신 {low('터전순위_통신')} | 상가 {low('체류형점포_순위')} | 경로당 {low('경로당_순위')}")


def main() -> None:
    g = build()
    assert len(g) == 47, f"동 {len(g)}개 (기대 47)"
    check(g)
    g.to_csv(OUT, index=False, encoding="utf-8-sig", lineterminator="\n")
    print(f"\n저장: {OUT.relative_to(ROOT)} ({len(g)}개 동)")


if __name__ == "__main__":
    main()
