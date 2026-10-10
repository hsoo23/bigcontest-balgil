"""독립 지표 대조 — 카드가 잡는 사람과 통신이 잡는 사람이 같은가 (B1, 타당성 검증 ③)

기획안 7절의 타당성 검증 ③은 "분석에 안 쓴 야간·주말 유동과의 상관"이었는데,
전제가 깨졌다. 저녁 비중(`evening`)이 좁아짐 분류 모델의 입력 11개에 이미 들어
있어서 "안 쓴 지표"가 아니다.

대신 **SK 통신 유동인구**를 쓴다. 재분석 코드(a0·b0·b1·b2·b3)는 SK를 한 줄도
읽지 않으므로 모델 경로와 완전히 독립이다. 카드의 성·연령 구성과 통신의 성·연령
구성을 맞대어, 카드가 특정 연령을 치우쳐 잡고 있지 않은지 본다.

SK는 연령과 시간의 교차표를 주지 않으므로(해상도 한계) 집단 단위에서 쓸 수 있는
것은 성·연령 구성뿐이다. 야간·주말은 동 단위로만 있어 집단 지표와 맞출 수 없다.

출력: data/processed/reanalysis/sk_independent.csv

실행: python scripts/explore_sk_independent.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from balgil.data import PROCESSED_DIR

OUT = PROCESSED_DIR / "reanalysis"
CITY = {"강남": "서울 강남구", "춘천": "강원 춘천시"}
BAND = ["10대", "20대", "30대", "40대", "50대", "60대 이상"]


def sk_share() -> pd.DataFrame:
    sk = pd.read_parquet(PROCESSED_DIR / "sk_age.parquet")
    cols = [c for c in sk.columns if "FLOW_POP_CNT" in c]
    t = sk.melt(id_vars=["SGG_NM"], value_vars=cols, var_name="col", value_name="flow")
    t["성별"] = np.where(t.col.str.startswith("WMAN"), "여성", "남성")
    code = t.col.str.extract(r"_(\d0)(GU|G)$")
    t["연령"] = np.where(code[1] == "GU", "60대 이상", code[0] + "대")
    g = t.groupby(["SGG_NM", "성별", "연령"], as_index=False).flow.sum()
    g["통신비중"] = g.flow / g.groupby(["SGG_NM", "성별"]).flow.transform("sum")
    return g


def card_share() -> pd.DataFrame:
    fs = pd.read_csv(OUT / "features_segment.csv")
    fs["SGG_NM"] = fs.city.map(CITY)
    fs["연령"] = np.where(fs.AGE.isin(["60대", "70대", "80대", "90대"]), "60대 이상", fs.AGE)
    g = fs.groupby(["SGG_NM", "성별" if "성별" in fs else "sex", "연령"], as_index=False).n.sum()
    g = g.rename(columns={"sex": "성별"})
    g["카드비중"] = g.n / g.groupby(["SGG_NM", "성별"]).n.transform("sum")
    return g


def main() -> None:
    m = sk_share().merge(card_share(), on=["SGG_NM", "성별", "연령"], how="inner")
    m["연령"] = pd.Categorical(m.연령, BAND, ordered=True)
    m = m.sort_values(["SGG_NM", "성별", "연령"])
    m["카드÷통신"] = (m.카드비중 / m.통신비중).round(2)

    print("■ 성·연령 구성 — 통신 대비 카드 (1.0이면 같은 비중)")
    print(m.pivot_table(index=["SGG_NM", "성별"], columns="연령", values="카드÷통신", observed=True).to_string())

    print("\n■ 구성 자체")
    for c in ["통신비중", "카드비중"]:
        print(f"  [{c}]")
        print(m.pivot_table(index=["SGG_NM", "성별"], columns="연령", values=c, observed=True).round(3).to_string())

    rows = []
    for (city, sex), g in m.groupby(["SGG_NM", "성별"]):
        rows.append({
            "도시": city, "성별": sex,
            "스피어만": g.통신비중.corr(g.카드비중, method="spearman"),
            "피어슨": g.통신비중.corr(g.카드비중),
            "카드÷통신 60대이상": float(g.loc[g.연령 == "60대 이상", "카드÷통신"].iloc[0]),
            "카드÷통신 10대": float(g.loc[g.연령 == "10대", "카드÷통신"].iloc[0]),
        })
    R = pd.DataFrame(rows).round(3)
    print("\n■ 구성 상관과 치우침")
    print(R.to_string(index=False))

    m.round(4).to_csv(OUT / "sk_independent.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {(OUT / 'sk_independent.csv').name}")


if __name__ == "__main__":
    main()
