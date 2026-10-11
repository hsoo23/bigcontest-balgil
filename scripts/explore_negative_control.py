"""B2 음성 대조 — 동별 터전 지표가 고령 1인세대율만 맞히는가.

기획안 「음성 대조」: SK 60대 이상 유동 비중으로 고령 1인세대율을 맞히는 것은 둘 다 연령 구성을 타므로
고립과 상관없이도 잘 나올 수 있다. 그래서 30·40대 1인세대율을 같은 방법으로 맞혀 본다.
고령에서만 맞고 30·40대에서는 맞지 않으면 "연령 구성 탓이 아니다"가 선다.

방법 (47개 동, 도시 효과를 지우려고 도시 안에서 본다)
  1 상관    동 패널 지표 6개와 1인세대율의 스피어만 상관 (강남 22, 춘천 25)
  2 분류    1인세대율 상위 20% vs 하위 20% 동을 60대 이상 비중 하나로 가르는 AUC (도시 안 순위 기준)

라벨: 행안부 「성/연령별 주민등록 1인세대수」 ÷ 「연령별 인구현황」, 2025년 12월 한 시점.
  고령 = 65세 이상, 30·40대 = 30~49세.

선행: python scripts/build_dong_panel.py, data/external/mois_single_household·mois_population (PR #10)
실행: python scripts/explore_negative_control.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402

EXT = ROOT / "data" / "external"
SGG = {"강남구": "서울 강남구", "춘천시": "강원 춘천시"}
BANDS = {"고령(65+)": range(65, 101), "30·40대": range(30, 50)}
FEATURES = ["60대이상_비중", "60대이상_여성비중", "저녁비중", "일요일_평일비", "겨울유지", "60대이상_규모"]


def read_mois(slug: str) -> pd.DataFrame:
    """동 × 나이(0~100) 표. 행정구역 '… 신북읍(5111025000)'에서 시군구·동 이름과 코드를 뽑는다."""
    frames = []
    for path in sorted((EXT / slug).glob("*.csv")):
        raw = pd.read_csv(path, encoding="cp949", thousands=",")
        sgg = next(v for k, v in SGG.items() if k in path.stem)
        area = raw.iloc[:, 0].str.extract(r"(?P<name>\S+)\s*\((?P<MOIS_CD>\d{10})\)$")
        ages = {c: int(re.search(r"_계_(\d+)세", c).group(1)) for c in raw.columns if re.search(r"_계_\d+세", c)}
        df = raw[list(ages)].rename(columns=ages)
        df.index = pd.MultiIndex.from_arrays([[sgg] * len(df), area["name"], area["MOIS_CD"]], names=["SGG_NM", "ADM_NM", "MOIS_CD"])
        frames.append(df[~area["MOIS_CD"].str.endswith("00000").values])  # 시군구 합계 행 제외
    return pd.concat(frames)


def auc(score: pd.Series, label: pd.Series) -> float:
    """label 1이 0보다 높은 점수를 받을 확률 (동점 0.5)."""
    pos, neg = score[label == 1].values, score[label == 0].values
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))


def main() -> None:
    hh, pop = read_mois("mois_single_household"), read_mois("mois_population")
    rate = pd.DataFrame({b: hh[list(r)].sum(axis=1) / pop[list(r)].sum(axis=1) * 100 for b, r in BANDS.items()})
    rate = rate.reset_index()

    panel = pd.read_parquet(PROCESSED_DIR / "features_dong.parquet")
    df = panel.merge(rate, on=["SGG_NM", "ADM_NM"], how="left")
    unmatched = df[df["MOIS_CD"].isna()]["ADM_NM"].tolist()
    print(f"행안부 연결: {df['MOIS_CD'].notna().sum()}/47" + (f" — 미연결 {unmatched}" if unmatched else ""))
    df = df.dropna(subset=["MOIS_CD"])

    print("\n■ 1인세대율 (%, 2025-12)")
    print(df.groupby("도시")[list(BANDS)].describe().loc[:, (slice(None), ["min", "50%", "max"])].round(1).to_string())

    print("\n■ 1. 도시 안 스피어만 상관 (지표 → 1인세대율)")
    rows = []
    for c, g in df.groupby("도시"):
        for f in FEATURES:
            rows.append({"도시": c, "지표": f, **{b: g[f].corr(g[b], method="spearman") for b in BANDS}})
    corr = pd.DataFrame(rows)
    print(corr.pivot(index="지표", columns="도시", values=list(BANDS)).round(2).to_string())
    pooled = {b: df["60대이상_비중"].corr(df[b], method="spearman") for b in BANDS}
    print("  참고 — 두 도시를 섞으면 60대이상_비중 상관:", {k: round(v, 2) for k, v in pooled.items()},
          "(도시 차이가 섞인 값이라 판단에 쓰지 않는다)")

    print("\n■ 2. 상위 20% vs 하위 20% 동을 60대 이상 비중으로 가르는 AUC (도시 안 순위)")
    out = []
    for b in BANDS:
        pct = df.groupby("도시")[b].rank(pct=True)
        sub = df[(pct >= 0.8) | (pct <= 0.2)]
        label = (pct[sub.index] >= 0.8).astype(int)
        score = df.groupby("도시")["60대이상_비중"].rank(pct=True)[sub.index]
        out.append({"라벨": b, "동 수(상위+하위)": len(sub), "AUC": round(auc(score, label), 3)})
    print(pd.DataFrame(out).to_string(index=False))


if __name__ == "__main__":
    main()
