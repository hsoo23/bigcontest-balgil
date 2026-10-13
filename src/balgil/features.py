"""고립 위험 지표의 정의.

업종 분류와 지표 산출식을 한 곳에 모은다. 분석 스크립트는 모두 여기를 참조한다.

지표는 두 축으로 나뉜다.
  역할 상실  : 평일화 지수 — 근로자의 생활 리듬에서 벗어난 정도 (카드)
  관계 자원  : 1인세대율 — 함께 사는 사람이 없는 정도 (행안부)
여기에 체류 소비 비중(발길의 질), 또래 활동, 인프라 공급량을 보조 지표로 붙인다.
"""
from __future__ import annotations

import pandas as pd

# 카드 업종 4분류 — 발길 확정안(실행계획 2절, 이슈 #8). 윤지 재분석 reanalysis/b0_common.py와 같다.
# 비중은 거주자 결제 건수로 재고, 분모는 분류 밖 업종(세금공과금 등)까지 포함한 전체 건수다.
# 머물며 얼굴을 익히는 곳 = 발길의 질.
STAY_MCT = [
    "커피전문점", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지", "노래방",
    "유흥업소", "스포츠시설", "헬스장", "실내/실외골프장", "학원/학습지",
]
# 차려진 음식을 사는 곳. 80대에 조리 대체로 늘어 체류와 섞으면 연령 경사가 흐려진다.
MEAL_MCT = ["한식", "중식", "일식", "양식", "기타요식"]
# 반복해도 얼굴을 기억하지 않는 곳.
ANON_MCT = ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매", "패스트푸드"]
# 건강 때문에 가는 곳. 끊김 판정에서 따로 떼어 헛알림을 줄인다.
MED_MCT = ["약국", "일반병원", "종합병원", "한의원", "치과병원", "기타의료", "보건소"]
# 넣지 않은 업종: 제과점(체류에 넣으면 강남 80대 반등이 생김, A5), 영화/공연·게임방/오락실 등
# 여가·여행 6개(주민이 머무는 곳이 아님, #8), 세금공과금 등. 모두 '기타'로 분모에만 남는다.
MCT_GROUPS = {"체류": STAY_MCT, "식사": MEAL_MCT, "익명": ANON_MCT, "병원·약국": MED_MCT}
_dup = [m for m in set(sum(MCT_GROUPS.values(), [])) if sum(m in g for g in MCT_GROUPS.values()) > 1]
assert not _dup, f"업종이 두 분류에 들어 있음: {_dup}"  # 예전 주류판매 중복(A3) 재발 방지

# 터전의 체류형 점포로 볼 상가업종 중분류(소상공인 상가정보 기준).
# 카드의 체류 업종과 성격을 맞췄다. 부분 문자열 패턴("음식|주점|커피|...")은
# 상가정보 어휘와 어긋나 커피('비알코올 ')·욕탕·유원지·도서관 4,547개를 놓쳤으므로
# 중분류명 전체를 정확히 비교한다. 중분류명 일부에 뒤쪽 공백이 있어 strip()이 필요하다.
# 카드 체류의 학원/학습지는 짝을 두지 않는다. 학원은 고령 주민이 머무는 터전과 관계가 없어 상가에서는 세지 않는다.
STAY_STORE_MID = ["비알코올", "이용·미용", "욕탕·신체관리", "스포츠 서비스", "주점"]

# 중분류 '유원지·오락'은 소분류 단위로 카드 체류와 맞춘다(이슈 #8, D안).
# 노래방은 카드 체류에도 있어 남기고, PC방·게임장(카드 게임방/오락실)과 기타 오락장·
# 수상레저·낚시터(카드 놀이동산 계열)는 카드처럼 뺀다. 주민이 머무는 곳이 아니다.
STAY_STORE_SUB = ["노래방"]

# 위 중분류 안에서도 카드 체류에 대응 업종이 없는 소분류는 뺀다(#8에서 C2로 넘긴 건, #4).
# 요리 주점은 카드에 일반 주점 업종이 없고(체류는 유흥업소만), 독서실/스터디 카페는
# 혼자 공부하러 가는 곳이라 카드 확정안에도 없다(중분류 '도서관·사적지'는 이것뿐이라 통째로 뺐다).
# 둘을 빼도 도시 안 동 순위 상관은 0.99 이상이고 하위 3개 동은 그대로다.
STAY_STORE_EXCLUDE_SUB = ["요리 주점"]

TARGET_AGES = ["50대", "60대"]
CONTROL_AGES = ["30대", "40대"]  # 기준선. 연령 효과를 제거하는 대조군이다.

NIGHT_HOURS = [f"TMST_{h:02d}" for h in (22, 23, 0, 1, 2, 3, 4)]
WEEKDAY_FLOW = ["FLOW_POP_CNT_MON", "FLOW_POP_CNT_TUS", "FLOW_POP_CNT_WED", "FLOW_POP_CNT_THU", "FLOW_POP_CNT_FRI"]
WEEKEND_FLOW = ["FLOW_POP_CNT_SAT", "FLOW_POP_CNT_SUN"]


def classify_mct(series: pd.Series) -> pd.Series:
    """업종명을 체류/식사/익명/병원·약국/기타로 분류한다."""
    lookup = {m: group for group, mcts in MCT_GROUPS.items() for m in mcts}
    return series.map(lookup).fillna("기타")


def is_stay_store(store: pd.DataFrame) -> pd.Series:
    """상가 점포가 체류형인지 판정한다. 중분류로 고르고 소분류로 넣고 뺀다.

    뒤쪽 공백을 지운 뒤 정확히 비교한다.
    """
    mid = store["상권업종중분류명"].str.strip()
    sub = store["상권업종소분류명"].str.strip()
    return (mid.isin(STAY_STORE_MID) & ~sub.isin(STAY_STORE_EXCLUDE_SUB)) | sub.isin(STAY_STORE_SUB)


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
