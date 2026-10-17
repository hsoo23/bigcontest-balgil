"""발길이 닿던 곳을 찾는 재료 두 가지를 만든다 (D1 find_counterpart).

1. 집단별 업종 쏠림 — 그 집단의 상대방 후보 업종(체류 11개 · 식사 5개 + 약국) 결제가 어느 업종에 몰려 있는가.
   비중은 후보 업종 결제 합을 분모로 하고, 같은 도시 전 연령 비중과 견준 쏠림(배수)을 같이 낸다.
   6개월 평소 값이다 — 끊긴 뒤가 아니라 "평소 발길이 닿던 업종"을 찾는 것이라서다.
2. 동별 업종 점포 수 — 카드 업종을 상가 소분류로 옮겨(대응표) 행정동마다 센다. 상호는 내지 않는다.

카드 업종 ↔ 상가 소분류 대응표: data/reference/card_store_map.csv
  카드 분류는 A1 확정안(features.MCT_GROUPS)과 같고, 상가 쪽은 #8 D안·#24(요리 주점 제외)와 맞췄다.
  상대방 후보는 체류·식사 업종과 약국이다. 장보기(편의점 등)는 "물어도 모른다"(기획안 3절)라 넣지 않는다.

선행: reanalysis/a0_load_clean.py (data/processed/reanalysis/card2.pkl),
      상가 원본 data/external/sbiz_store/*.csv (없으면 2는 건너뜀)
실행: python scripts/build_segment_industry.py
산출: data/processed/segment_industry.parquet, data/processed/dong_industry_stores.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402
from balgil.features import MEAL_MCT, STAY_MCT  # noqa: E402

MAP_PATH = ROOT / "data" / "reference" / "card_store_map.csv"
STORE_DIR = ROOT / "data" / "external" / "sbiz_store"
SGG = {"강남구": "서울 강남구", "춘천시": "강원 춘천시"}
COUNTERPART = STAY_MCT + MEAL_MCT + ["약국"]


def segment_industry() -> pd.DataFrame:
    card = pd.read_pickle(PROCESSED_DIR / "reanalysis" / "card2.pkl")
    card = card[card["resident"] & card["ind"].isin(COUNTERPART)]
    g = card.groupby(["city", "sex", "AGE", "ind"])["cnt"].sum().rename("건수").reset_index()
    g["비중"] = g["건수"] / g.groupby(["city", "sex", "AGE"])["건수"].transform("sum")
    city = card.groupby(["city", "ind"])["cnt"].sum()
    g["도시전체비중"] = [city[(c, i)] / city[c].sum() for c, i in zip(g["city"], g["ind"])]
    g["쏠림"] = g["비중"] / g["도시전체비중"]
    g["순위"] = g.groupby(["city", "sex", "AGE"])["비중"].rank(ascending=False, method="first").astype(int)
    group = {**{m: "체류" for m in STAY_MCT}, **{m: "식사" for m in MEAL_MCT}, "약국": "병원·약국"}
    return g.rename(columns={"ind": "업종"}).assign(발길분류=lambda d: d["업종"].map(group)).sort_values(["city", "sex", "AGE", "순위"])


def dong_industry_stores(cmap: pd.DataFrame) -> pd.DataFrame | None:
    files = sorted(STORE_DIR.glob("*.csv"))
    if not files:
        print("상가 원본이 없어 동별 업종 점포 수는 건너뜁니다 (data/external/sbiz_store/)")
        return None
    cols = ["시군구명", "행정동명", "상권업종중분류명", "상권업종소분류명"]
    store = pd.concat(pd.read_csv(f, usecols=cols, dtype=str) for f in files)
    store = store[store["시군구명"].isin(SGG)].assign(SGG_NM=lambda d: d["시군구명"].map(SGG))
    mid, sub = store["상권업종중분류명"].str.strip(), store["상권업종소분류명"].str.strip()
    unknown = set(cmap.loc[cmap["상가단계"] == "중분류", "상가이름"]) - set(mid) | set(cmap.loc[cmap["상가단계"] == "소분류", "상가이름"]) - set(sub)
    assert not unknown, f"대응표의 상가 이름이 원본에 없음: {unknown}"
    out = []
    for card_ind, rows in cmap.groupby("카드업종"):
        hit = pd.Series(False, index=store.index)
        for r in rows.itertuples():
            hit |= (mid == r.상가이름) if r.상가단계 == "중분류" else (sub == r.상가이름)
        for e in rows.loc[rows["상가단계"] == "제외", "상가이름"]:
            hit &= sub != e
        out.append(store[hit].groupby(["SGG_NM", "행정동명"]).size().rename("점포수").reset_index().assign(업종=card_ind))
    return pd.concat(out).rename(columns={"행정동명": "ADM_NM"})


def main() -> None:
    cmap = pd.read_csv(MAP_PATH, encoding="utf-8-sig")
    assert set(cmap["카드업종"]) == set(COUNTERPART), f"대응표 업종이 후보 업종과 다름: {set(COUNTERPART) ^ set(cmap['카드업종'])}"

    seg = segment_industry()
    seg.to_parquet(PROCESSED_DIR / "segment_industry.parquet", index=False)
    print(f"저장: data/processed/segment_industry.parquet ({len(seg)}행)")
    old = seg[seg["AGE"].isin(["60대", "70대", "80대"]) & (seg["순위"] <= 3)]
    print(old.assign(비중=lambda d: (d["비중"] * 100).round(1), 쏠림=lambda d: d["쏠림"].round(2))
          .pivot_table(index=["city", "sex", "AGE"], columns="순위", values="업종", aggfunc="first").to_string())

    stores = dong_industry_stores(cmap)
    if stores is not None:
        stores.to_parquet(PROCESSED_DIR / "dong_industry_stores.parquet", index=False)
        print(f"\n저장: data/processed/dong_industry_stores.parquet ({stores['ADM_NM'].nunique()}개 동 × {stores['업종'].nunique()}업종)")
        print(stores.groupby("업종")["점포수"].sum().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
