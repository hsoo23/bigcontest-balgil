"""독립 지표 대조 — 카드·통신·주민등록이 같은 사람을 잡는가 (B1, 타당성 검증 ③)

기획안 7절의 타당성 검증 ③은 "분석에 안 쓴 야간·주말 유동과의 상관"이었는데,
전제가 깨졌다. 저녁 비중(`evening`)이 좁아짐 분류 모델의 입력 11개에 이미 들어
있어서 "안 쓴 지표"가 아니다.

대신 **SK 통신 유동인구**를 쓴다. 재분석 코드(a0·b0·b1·b2·b3)는 SK를 한 줄도
읽지 않으므로 모델 경로와 완전히 독립이다.

다만 카드와 통신은 **모집단이 다르다.** 카드는 시도 거주자의 결제(`a0_load_clean.py`의
`resident`)이고 통신은 그 지역에 있었던 사람 전체(외지 방문자 포함)다. 둘만 맞대면
차이가 카드 치우침인지 방문자 구성인지 가릴 수 없다.

그래서 **행안부 주민등록 인구를 세 번째 기준**으로 넣는다. 주민등록은 거주자의
실제 연령 구조이므로, 카드와 통신이 각각 거기서 얼마나 벗어나는지 보면
어느 쪽 치우침인지 가려진다.

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


def mois_share() -> pd.DataFrame:
    """행안부 주민등록 인구 — 거주자의 실제 연령 구조(기준선)."""
    import re
    rows = []
    for f in sorted((PROCESSED_DIR.parent / "external" / "mois_population").glob("*.csv")):
        raw = pd.read_csv(f, encoding="cp949", thousands=",")
        reg = raw["행정구역"].astype(str)
        keep = reg.str.contains(r"\(\d+\)$") & (reg.str.split().str.len() >= 3)  # 읍면동 행만
        sgg = "서울 강남구" if "강남" in f.name else "강원 춘천시"
        for col in raw.columns[1:]:
            m = re.fullmatch(r"\d{4}년\d{2}월_(남|여)_(\d{1,3})세( 이상)?", col)
            if not m:
                continue
            age = int(m.group(2))
            if age < 10:
                continue
            band = "60대 이상" if age >= 60 else f"{age // 10 * 10}대"
            rows.append((sgg, {"남": "남성", "여": "여성"}[m.group(1)], band,
                         pd.to_numeric(raw.loc[keep, col], errors="coerce").sum()))
    g = pd.DataFrame(rows, columns=["SGG_NM", "성별", "연령", "인구"]).groupby(
        ["SGG_NM", "성별", "연령"], as_index=False).인구.sum()
    g["주민등록비중"] = g.인구 / g.groupby(["SGG_NM", "성별"]).인구.transform("sum")
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
    m = (sk_share()
         .merge(card_share(), on=["SGG_NM", "성별", "연령"], how="inner")
         .merge(mois_share()[["SGG_NM", "성별", "연령", "주민등록비중"]],
                on=["SGG_NM", "성별", "연령"], how="left"))
    m["연령"] = pd.Categorical(m.연령, BAND, ordered=True)
    m = m.sort_values(["SGG_NM", "성별", "연령"])
    m["카드÷통신"] = (m.카드비중 / m.통신비중).round(2)
    m["카드÷주민등록"] = (m.카드비중 / m.주민등록비중).round(2)
    m["통신÷주민등록"] = (m.통신비중 / m.주민등록비중).round(2)

    print("■ 주민등록 인구 대비 (1.0이면 거주 인구 구조와 같음)")
    for c in ["카드÷주민등록", "통신÷주민등록", "카드÷통신"]:
        print(f"  [{c}]")
        print(m.pivot_table(index=["SGG_NM", "성별"], columns="연령", values=c, observed=True).to_string())

    print("\n■ 구성 자체")
    for c in ["주민등록비중", "통신비중", "카드비중"]:
        print(f"  [{c}]")
        print(m.pivot_table(index=["SGG_NM", "성별"], columns="연령", values=c, observed=True).round(3).to_string())

    rows = []
    for (city, sex), g in m.groupby(["SGG_NM", "성별"]):
        rows.append({
            "도시": city, "성별": sex,
            "카드-주민 상관": g.주민등록비중.corr(g.카드비중, method="spearman"),
            "통신-주민 상관": g.주민등록비중.corr(g.통신비중, method="spearman"),
            "카드-통신 상관": g.통신비중.corr(g.카드비중, method="spearman"),
            "카드÷주민 60대이상": float(g.loc[g.연령 == "60대 이상", "카드÷주민등록"].iloc[0]),
            "통신÷주민 60대이상": float(g.loc[g.연령 == "60대 이상", "통신÷주민등록"].iloc[0]),
            "카드÷주민 10대": float(g.loc[g.연령 == "10대", "카드÷주민등록"].iloc[0]),
            "통신÷주민 10대": float(g.loc[g.연령 == "10대", "통신÷주민등록"].iloc[0]),
        })
    R = pd.DataFrame(rows).round(3)
    print("\n■ 구성 상관과 치우침")
    print(R.to_string(index=False))

    m.round(4).to_csv(OUT / "sk_independent.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {(OUT / 'sk_independent.csv').name}")


if __name__ == "__main__":
    main()
