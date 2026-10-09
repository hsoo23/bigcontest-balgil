"""고립 위험 지표의 정의.

업종 분류와 지표 산출식을 한 곳에 모은다. 분석 스크립트는 모두 여기를 참조한다.

지표는 두 축으로 나뉜다.
  역할 상실  : 평일화 지수 — 근로자의 생활 리듬에서 벗어난 정도 (카드)
  관계 자원  : 1인세대율 — 함께 사는 사람이 없는 정도 (행안부)
여기에 사회적 소비 결핍도, 또래 활동, 인프라 공급량을 보조 지표로 붙인다.
"""
from __future__ import annotations

import pandas as pd

# 타인과의 접촉을 동반하는 소비. 이 분류 자체가 분석의 핵심 산출물이므로
# 팀 논의로 확정해야 하며, 보고서에 기준과 함께 싣는다.
SOCIAL_MCT = [
    "한식", "중식", "일식", "양식", "기타요식", "패스트푸드", "커피전문점", "제과점",
    "노래방", "유흥업소", "영화/공연", "종합레저타운/놀이동산", "스포츠시설", "헬스장",
    "실내/실외골프장", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지",
    "게임방/오락실", "예식장/결혼서비스", "호텔/콘도", "여행사/항공사", "학원/학습지", "주류판매",
]
# 혼자 소비하고 끝나는 업종. 사회적 소비가 이쪽으로 대체되는지 본다.
ALONE_MCT = ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매"]
# 생존에 필요해 고립 여부와 무관하게 발생하는 소비.
ESSENTIAL_MCT = [
    "약국", "일반병원", "종합병원", "한의원", "치과병원", "기타의료",
    "세금공과금", "통신요금(이동,시내전화)", "생활잡화/수입상품점",
]

# 터전의 체류형 점포로 볼 상가업종 중분류(소상공인 상가정보 기준).
# 카드의 체류 업종과 성격을 맞췄다. 부분 문자열 패턴("음식|주점|커피|...")은
# 상가정보 어휘와 어긋나 커피('비알코올 ')·욕탕·유원지·도서관 4,547개를 놓쳤으므로
# 중분류명 전체를 정확히 비교한다. 중분류명 일부에 뒤쪽 공백이 있어 strip()이 필요하다.
# 유원지·오락 포함 여부는 카드 체류 범위와 맞추는 문제로 이슈 #8에서 결정한다.
STAY_STORE_MID = ["비알코올", "이용·미용", "욕탕·신체관리", "스포츠 서비스", "유원지·오락", "주점", "도서관·사적지"]

TARGET_AGES = ["50대", "60대"]
CONTROL_AGES = ["30대", "40대"]  # 기준선. 연령 효과를 제거하는 대조군이다.

NIGHT_HOURS = [f"TMST_{h:02d}" for h in (22, 23, 0, 1, 2, 3, 4)]
WEEKDAY_FLOW = ["FLOW_POP_CNT_MON", "FLOW_POP_CNT_TUS", "FLOW_POP_CNT_WED", "FLOW_POP_CNT_THU", "FLOW_POP_CNT_FRI"]
WEEKEND_FLOW = ["FLOW_POP_CNT_SAT", "FLOW_POP_CNT_SUN"]


def classify_mct(series: pd.Series) -> pd.Series:
    """업종명을 사회적/혼자형/필수/기타로 분류한다."""
    return pd.Series(
        [
            "사회적" if x in SOCIAL_MCT else "혼자형" if x in ALONE_MCT else "필수" if x in ESSENTIAL_MCT else "기타"
            for x in series
        ],
        index=series.index,
    )


def is_stay_store(mid: pd.Series) -> pd.Series:
    """상가 중분류명이 체류형 점포인지 판정한다. 뒤쪽 공백을 지운 뒤 정확히 비교한다."""
    return mid.str.strip().isin(STAY_STORE_MID)


def resident_only(card: pd.DataFrame) -> pd.DataFrame:
    """가맹점 지역과 고객 거주지가 일치하는 결제만 남긴다.

    강남은 외지 결제가 많아 그대로 쓰면 주민의 생활 패턴이 아니라 방문객 패턴이 된다.
    """
    return card[
        ((card["MCT_SGG_CD"] == "서울 강남구") & (card["CLN_SGG_CD"] == "서울"))
        | ((card["MCT_SGG_CD"] == "강원 춘천시") & (card["CLN_SGG_CD"] == "강원"))
    ]


def gap_to_control(df: pd.DataFrame, value: str, keys: list[str]) -> pd.Series:
    """같은 지역·월 안에서 30·40대 평균 대비 격차를 구한다.

    지역 차이와 계절 효과를 동시에 제거한다. 값이 음수면 대조군보다 낮다는 뜻이다.
    """
    base = (
        df[df["AGE_CCD"].isin(CONTROL_AGES)]
        .groupby(keys)[value]
        .mean()
        .rename("_base")
    )
    merged = df.merge(base, left_on=keys, right_index=True, how="left")
    return (merged[value] - merged["_base"]).set_axis(df.index)
