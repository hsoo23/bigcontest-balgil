"""방향성 후보의 근거가 되는 고립 신호 지표를 계산한다.

회의 자료(docs/방향성_회의자료.md)와 이슈 #1에 인용된 숫자의 재현용 스크립트이다.
사전에 scripts/build_processed.py를 실행해 data/processed/*.parquet이 있어야 한다.

실행: python scripts/explore_signals.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR

AGE_ORDER = ["10대", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대"]

# 타인과의 접촉을 동반하는 소비(관계형 소비)로 분류한 업종.
# 후보 A를 채택할 경우 이 분류 자체가 핵심 산출물이 되므로 팀 논의로 확정해야 한다.
SOCIAL = [
    "한식", "중식", "일식", "양식", "기타요식", "패스트푸드", "커피전문점", "제과점",
    "노래방", "유흥업소", "영화/공연", "종합레저타운/놀이동산", "스포츠시설", "헬스장",
    "실내/실외골프장", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지",
    "게임방/오락실", "예식장/결혼서비스", "호텔/콘도", "여행사/항공사", "학원/학습지", "주류판매",
]
ESSENTIAL = [
    "편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "약국",
    "일반병원", "종합병원", "한의원", "치과병원", "기타의료", "세금공과금",
    "통신요금(이동,시내전화)", "생활잡화/수입상품점",
]

NIGHT_HOURS = [f"TMST_{h:02d}" for h in (22, 23, 0, 1, 2, 3, 4)]
DAY_HOURS = [f"TMST_{h:02d}" for h in range(9, 18)]
WEEKDAY_COLS = ["FLOW_POP_CNT_MON", "FLOW_POP_CNT_TUS", "FLOW_POP_CNT_WED", "FLOW_POP_CNT_THU", "FLOW_POP_CNT_FRI"]
WEEKEND_COLS = ["FLOW_POP_CNT_SAT", "FLOW_POP_CNT_SUN"]


def card_signals() -> None:
    card = pd.read_parquet(PROCESSED_DIR / "card_resid.parquet")
    card["소비유형"] = card["MCT_RY_CD"].map(lambda x: "관계형" if x in SOCIAL else ("필수" if x in ESSENTIAL else "기타"))

    cnt = card.groupby(["MCT_SGG_CD", "AGE_CCD", "소비유형"])["USE_CNT"].sum().unstack(fill_value=0)
    print("■ 관계형 소비 건수 비중 (연령 x 지역)")
    print((cnt["관계형"] / cnt.sum(axis=1)).unstack(0).reindex(AGE_ORDER).round(3).to_string(), "\n")

    chuncheon = card[card["MCT_SGG_CD"] == "강원 춘천시"].copy()
    chuncheon["is_local"] = chuncheon["CLN_SGG_CD"].eq("강원")
    local = chuncheon.groupby(["AGE_CCD", "is_local"])["USE_CNT"].sum().unstack(fill_value=0)
    print("■ 춘천 결제 중 강원 거주 고객 비중 (연령별)")
    print((local[True] / local.sum(axis=1)).reindex(AGE_ORDER).round(3).to_string(), "\n")

    card_time = pd.read_parquet(PROCESSED_DIR / "card_time.parquet")
    card_time = card_time[~card_time["IS_CORP"]]
    slot = card_time.groupby(["MCT_SGG_CD", "AGE_CCD", "TIME_GB"])["USE_CNT"].sum().unstack(fill_value=0)
    print("■ 시간대별 결제 비중 (연령 x 지역)")
    print(slot.div(slot.sum(axis=1), axis=0).round(3).to_string(), "\n")


def flow_signals() -> pd.DataFrame:
    """행정동 단위 유동인구 지표를 계산해 반환한다."""
    time_df = pd.read_parquet(PROCESSED_DIR / "sk_time.parquet")
    hours = [f"TMST_{h:02d}" for h in range(24)]
    time_df["tot"], time_df["night"], time_df["day"] = time_df[hours].sum(1), time_df[NIGHT_HOURS].sum(1), time_df[DAY_HOURS].sum(1)
    by_month = time_df.groupby(["SGG_NM", "ADM_CD", "STD_YM"])[["tot", "night", "day"]].sum()
    by_month["night_r"] = by_month["night"] / by_month["tot"]
    by_month["day_r"] = by_month["day"] / by_month["tot"]
    dong = by_month.groupby(level=["SGG_NM", "ADM_CD"])[["night_r", "day_r"]].mean()
    dong["night_r_월변동"] = by_month.groupby(level=["SGG_NM", "ADM_CD"])["night_r"].std()

    wkdy = pd.read_parquet(PROCESSED_DIR / "sk_wkdy.parquet").groupby(["SGG_NM", "ADM_CD"])[WEEKDAY_COLS + WEEKEND_COLS].sum()
    dong["주말비"] = (wkdy[WEEKEND_COLS].sum(1) / 2) / (wkdy[WEEKDAY_COLS].sum(1) / 5)

    age = pd.read_parquet(PROCESSED_DIR / "sk_age.parquet")
    pop_cols = [c for c in age.columns if "FLOW_POP" in c]
    old_cols = [c for c in pop_cols if c.endswith("60GU")]
    ag = age.groupby(["SGG_NM", "ADM_CD"])[pop_cols].sum()
    dong["고령비중"] = ag[old_cols].sum(1) / ag[pop_cols].sum(1)
    dong["여성비"] = ag[[c for c in pop_cols if c.startswith("WMAN")]].sum(1) / ag[pop_cols].sum(1)

    print("■ 행정동 지표 분포 (47개 동)")
    print(dong.groupby(level="SGG_NM").agg(["mean", "min", "max"]).T.round(3).to_string(), "\n")
    print("■ 지표 간 상관")
    print(dong[["night_r", "day_r", "주말비", "고령비중", "여성비"]].corr().round(2).to_string(), "\n")
    print("■ 고령비중 상·하위 5개 동")
    ordered = dong.sort_values("고령비중")
    print(pd.concat([ordered.head(5), ordered.tail(5)]).round(3).to_string())
    return dong


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    card_signals()
    flow_signals()
