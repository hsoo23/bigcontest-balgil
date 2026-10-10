"""고립 위험 지표를 산출해 분석용 피처 테이블을 만든다.

산출 단위: 행정동 47개 × 월 6개 × 성별 2개 × 연령대 4개(30·40대는 대조군)

지표 구성
  역할 상실  : 평일화 지수(평일/주말 결제비, 평일 낮 결제 비중) — 카드, 시군구 단위
  관계 자원  : 1인세대율 — 행안부, 행정동 단위
  발길의 질  : 체류·식사·익명 소비 비중과 체류 비중의 대조군 대비 격차 — 카드, 시군구 단위
  또래·활동  : 동별 5060 유동인구 비중, 야간 활동 비중, 주말 유동비 — SK, 행정동 단위
  인프라     : 체류형 점포 수와 인구 대비 밀도 — 상가정보, 행정동 단위

주의: 카드 데이터의 공간 단위는 시군구 2개뿐이다. 카드 기반 지표는 같은 시군구의
행정동에 동일한 값이 부여되며, 행정동 간 차이는 유동인구·1인세대·인프라 지표가 만든다.
이 한계는 보고서에 명시한다.

실행: python scripts/build_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR
from balgil.features import (
    CONTROL_AGES,
    NIGHT_HOURS,
    TARGET_AGES,
    WEEKDAY_FLOW,
    WEEKEND_FLOW,
    classify_mct,
    gap_to_control,
    is_stay_store,
    resident_only,
)

AGES = TARGET_AGES + CONTROL_AGES
SEXES = ["남성", "여성"]


def card_consumption() -> pd.DataFrame:
    """체류·식사·익명 소비 비중과 체류 비중의 대조군 대비 격차 (시군구 × 성 × 연령 × 월).

    분모는 분류 밖 업종('기타')까지 포함한 전체 건수다(실행계획 2절).
    """
    card = resident_only(pd.read_parquet(PROCESSED_DIR / "card_resid.parquet"))
    card = card[card["AGE_CCD"].isin(AGES)].copy()
    card["소비유형"] = classify_mct(card["MCT_RY_CD"])
    card["STD_YM"] = card["TA_YMD"].dt.strftime("%Y%m")

    grp = card.groupby(["MCT_SGG_CD", "STD_YM", "SEX_CCD", "AGE_CCD", "소비유형"])["USE_CNT"].sum().unstack(fill_value=0)
    out = (grp.div(grp.sum(axis=1), axis=0)[["체류", "식사", "익명"]] * 100).reset_index()
    out.columns = ["SGG_NM", "STD_YM", "SEX_CCD", "AGE_CCD", "체류비중", "식사비중", "익명비중"]
    out["체류비중_대조군격차"] = gap_to_control(out, "체류비중", ["SGG_NM", "STD_YM", "SEX_CCD"])
    return out


def card_weekday() -> pd.DataFrame:
    """평일화 지수 (시군구 × 성 × 연령 × 월). 역할 상실의 대리 지표."""
    card = pd.read_parquet(PROCESSED_DIR / "card_time.parquet")
    card = card[~card["IS_CORP"] & card["AGE_CCD"].isin(AGES)].copy()
    card["STD_YM"] = card["TA_YMD"].dt.strftime("%Y%m")
    card["평일"] = card["TA_YMD"].dt.dayofweek < 5

    keys = ["MCT_SGG_CD", "STD_YM", "SEX_CCD", "AGE_CCD"]
    span = card.groupby(keys + ["평일"])["TA_YMD"].nunique().unstack()  # 월마다 평일·주말 일수가 다르다
    cnt = card.groupby(keys + ["평일"])["USE_CNT"].sum().unstack(fill_value=0)
    weekday_ratio = (cnt[True] / span[True]) / (cnt[False] / span[False])

    day = card[card["평일"]].groupby(keys + ["TIME_GB"])["USE_CNT"].sum().unstack(fill_value=0)
    daytime_share = day[["06_11", "12_17"]].sum(axis=1) / day.sum(axis=1) * 100

    out = pd.DataFrame({"평일주말비": weekday_ratio, "평일낮결제비중": daytime_share}).reset_index()
    out = out.rename(columns={"MCT_SGG_CD": "SGG_NM"})
    for col in ("평일주말비", "평일낮결제비중"):
        out[f"{col}_대조군격차"] = gap_to_control(out, col, ["SGG_NM", "STD_YM", "SEX_CCD"])
    return out


def flow_by_dong() -> pd.DataFrame:
    """행정동 × 월 유동인구 지표."""
    cell = pd.read_parquet(PROCESSED_DIR / "sk_cell_adm.parquet")[["BLOCK_CD", "X_COORD", "Y_COORD", "ADM_CD", "ADM_NM"]]
    key = ["BLOCK_CD", "X_COORD", "Y_COORD"]

    def to_dong(kind: str) -> pd.DataFrame:
        df = pd.read_parquet(PROCESSED_DIR / f"sk_{kind}.parquet").drop(columns=["ADM_CD", "SGG_CD"], errors="ignore")
        return df.merge(cell, on=key, how="inner").groupby(["ADM_CD", "ADM_NM", "SGG_NM", "STD_YM"]).sum(numeric_only=True)

    age = to_dong("age")
    pop_cols = [c for c in age.columns if "FLOW_POP" in c]
    older = [c for c in pop_cols if c.endswith(("50G", "60GU"))]
    out = pd.DataFrame(
        {
            "유동인구": age[pop_cols].sum(axis=1),
            "유동_5060이상비중": age[older].sum(axis=1) / age[pop_cols].sum(axis=1) * 100,
            "유동_여성비중": age[[c for c in pop_cols if c.startswith("WMAN")]].sum(axis=1) / age[pop_cols].sum(axis=1) * 100,
        }
    )

    tim = to_dong("time")
    hours = [c for c in tim.columns if c.startswith("TMST")]
    out["야간활동비중"] = tim[NIGHT_HOURS].sum(axis=1) / tim[hours].sum(axis=1) * 100

    wk = to_dong("wkdy")
    out["주말유동비"] = (wk[WEEKEND_FLOW].sum(axis=1) / 2) / (wk[WEEKDAY_FLOW].sum(axis=1) / 5)
    return out.reset_index().drop(columns="X_COORD", errors="ignore")


def dong_static() -> pd.DataFrame:
    """1인세대율(성·연령별)과 인프라 공급량(행정동)."""
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    hh = hh[hh["연령대"].isin(AGES)][["ADM_CD", "성별", "연령대", "일인세대수", "인구수", "일인세대율"]]
    hh = hh.rename(columns={"성별": "SEX_CCD", "연령대": "AGE_CCD"})
    hh["일인세대율"] = hh["일인세대율"] * 100

    store = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet")
    stay = store[is_stay_store(store)]
    infra = pd.DataFrame(
        {"점포수": store.groupby("ADM_CD").size(), "체류형점포수": stay.groupby("ADM_CD").size()}
    ).fillna(0).reset_index()
    return hh.merge(infra, on="ADM_CD", how="left")


def main() -> None:
    consumption, weekday, flow, static = card_consumption(), card_weekday(), flow_by_dong(), dong_static()

    features = (
        flow.merge(pd.DataFrame({"SEX_CCD": SEXES}), how="cross")
        .merge(pd.DataFrame({"AGE_CCD": AGES}), how="cross")
        .merge(consumption, on=["SGG_NM", "STD_YM", "SEX_CCD", "AGE_CCD"], how="left")
        .merge(weekday, on=["SGG_NM", "STD_YM", "SEX_CCD", "AGE_CCD"], how="left")
        .merge(static, on=["ADM_CD", "SEX_CCD", "AGE_CCD"], how="left")
    )
    features["체류형점포_대상천명당"] = features["체류형점포수"] / features["인구수"] * 1000  # 해당 성·연령 인구 1,000명당
    features["대상여부"] = features["AGE_CCD"].isin(TARGET_AGES)

    # A4 동 패널(features_dong.parquet, 47동)과 이름이 겹치지 않게 단위를 이름에 넣는다.
    features.to_parquet(PROCESSED_DIR / "features_dong_month.parquet", index=False)
    print(f"피처 테이블 {features.shape[0]:,}행 × {features.shape[1]}열 "
          f"(행정동 {features['ADM_CD'].nunique()} × 월 {features['STD_YM'].nunique()} × 성별 2 × 연령대 {len(AGES)})")
    missing = features.isna().sum()
    print("결측:", missing[missing > 0].to_dict() or "없음")

    cols = ["평일주말비_대조군격차", "체류비중_대조군격차", "일인세대율", "체류형점포_대상천명당", "야간활동비중"]
    print("\n■ 5060 지표 요약 (2025-12)")
    view = features[(features["대상여부"]) & (features["STD_YM"] == "202512")]
    print(view.groupby(["SGG_NM", "SEX_CCD", "AGE_CCD"])[cols].mean().round(2).to_string())

    print("\n■ 5060 남성 위험 상위 5개 행정동 (2025-12, 평일화 격차 × 1인세대율)")
    male = view[view["SEX_CCD"] == "남성"].groupby(["SGG_NM", "ADM_NM"])[cols].mean()
    male["위험점수"] = male[["평일주말비_대조군격차", "일인세대율"]].apply(lambda s: (s - s.mean()) / s.std()).sum(axis=1)
    print(male.sort_values("위험점수", ascending=False).head(5).round(2).to_string())


if __name__ == "__main__":
    main()
