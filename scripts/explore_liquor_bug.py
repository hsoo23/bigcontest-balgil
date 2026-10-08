"""`주류판매` 중복 버그 재현 (A3 사전작업).

`features.py`에서 `주류판매`가 `SOCIAL_MCT`와 `ALONE_MCT` 양쪽에 들어가 있다.
`classify_mct()`는 `SOCIAL_MCT`부터 검사하므로 주류판매는 항상 '사회적'으로 분류된다.
`build_features.card_consumption()`과 같은 계산을 기존 분류와 수정안(혼자형으로만)으로
각각 돌려, 지표가 얼마나 달라지는지 본다.

    python scripts/explore_liquor_bug.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil import features
from balgil.data import load_card
from balgil.features import CONTROL_AGES, TARGET_AGES, classify_mct, gap_to_control, resident_only

AGES = TARGET_AGES + CONTROL_AGES
KEYS = ["MCT_SGG_CD", "STD_YM", "SEX_CCD", "AGE_CCD"]


def consumption(card: pd.DataFrame) -> pd.DataFrame:
    """build_features.card_consumption()과 같은 계산 (소비유형 열은 미리 붙여서 받는다)."""
    grp = card.groupby(KEYS + ["소비유형"])["USE_CNT"].sum().unstack(fill_value=0)
    out = (grp.div(grp.sum(axis=1), axis=0)[["사회적", "혼자형"]] * 100).reset_index()
    out.columns = ["SGG_NM", "STD_YM", "SEX_CCD", "AGE_CCD", "사회적소비비중", "혼자형소비비중"]
    out["사회적소비_대조군격차"] = gap_to_control(out, "사회적소비비중", ["SGG_NM", "STD_YM", "SEX_CCD"])
    return out.set_index(["SGG_NM", "STD_YM", "SEX_CCD", "AGE_CCD"])


def main() -> None:
    card = resident_only(load_card("card_resid"))
    card = card[card["AGE_CCD"].isin(AGES)].copy()
    card["STD_YM"] = card["TA_YMD"].dt.strftime("%Y%m")

    # 1. 버그 확인: 주류판매가 어디로 분류되는가
    before = classify_mct(card["MCT_RY_CD"])
    liquor = card["MCT_RY_CD"].eq("주류판매")
    print("■ 1. 기존 classify_mct()에서 주류판매의 분류")
    print(before[liquor].value_counts().to_string(), "\n")

    # 2. 수정안: SOCIAL_MCT에서 주류판매를 빼고 ALONE_MCT에만 둔다
    fixed_social = [m for m in features.SOCIAL_MCT if m != "주류판매"]
    after = pd.Series(
        ["사회적" if x in fixed_social else "혼자형" if x in features.ALONE_MCT
         else "필수" if x in features.ESSENTIAL_MCT else "기타" for x in card["MCT_RY_CD"]],
        index=card.index,
    )
    print("■ 2. 수정안에서 주류판매의 분류")
    print(after[liquor].value_counts().to_string(), "\n")

    total = card["USE_CNT"].sum()
    print(f"■ 3. 대상 결제 중 주류판매 비중: {card.loc[liquor, 'USE_CNT'].sum() / total * 100:.3f}% "
          f"({card.loc[liquor, 'USE_CNT'].sum():,} / {total:,}건, 거주자·30~60대)\n")

    a = consumption(card.assign(소비유형=before))
    b = consumption(card.assign(소비유형=after))
    diff = (b - a)

    print(f"■ 4. 지표 변화 (수정안 − 기존, %p) · 셀 {len(diff)}개 = 시군구 2 × 월 6 × 성 2 × 연령 4")
    print(diff.abs().agg(["mean", "max"]).round(3).to_string(), "\n")

    print("■ 5. 사회적소비비중 변화가 가장 큰 셀 5개")
    top = diff["사회적소비비중"].abs().sort_values(ascending=False).head(5).index
    show = pd.DataFrame({"기존": a.loc[top, "사회적소비비중"], "수정안": b.loc[top, "사회적소비비중"],
                         "차이": diff.loc[top, "사회적소비비중"]}).round(3)
    print(show.to_string(), "\n")

    # 6. 연령 순서가 바뀌는가 (시군구 × 월 × 성별로 사회적소비비중 순위 비교)
    rank = lambda d: d["사회적소비비중"].groupby(level=["SGG_NM", "STD_YM", "SEX_CCD"]).rank()
    changed = (rank(a) != rank(b)).sum()
    print(f"■ 6. 사회적소비비중 연령 순위가 바뀐 셀: {changed}개 / {len(a)}개")


if __name__ == "__main__":
    main()
