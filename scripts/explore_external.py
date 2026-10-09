"""확보한 외부 데이터가 「발길」 틀에 실제로 꽂히는지 점검하고, 계절성을 확인한다.

이 스크립트는 세 가지를 한다.

  1 외부 데이터 7종의 해상도 점검
      발길의 터전 축은 행정동 단위다. 자원 데이터가 시군구 단위면 "어느 동에
      무엇을 배치하라"를 말할 수 없다. 어디까지 되는지 실제로 확인한다.

  2 체류형 점포 재집계  ← 버그 수정
      features.py가 쓰던 패턴 "음식|주점|커피|체육|여가|미용|스포츠"는
      상가정보 중분류명과 어휘가 어긋난다. 커피전문점은 중분류명이
      '비알코올 '(뒤에 공백)이라 패턴에 안 걸리고 2,950개가 통째로 빠졌다.
      그 결과 기획안이 인용한 "북산면 관계형 점포 0개"가 사실과 다르다.

  3 계절성 점검  ← 모델 설계에 직결
      공통 충격 보정을 "전 연령이 함께 떨어진 만큼 제거"로 설계했는데,
      겨울에는 연령대가 같은 방향으로 움직이지 않는다. 업종별로 방향이
      반대이기 때문이다(목욕탕 상승, 골프장 하락). 보정 기준선을
      연령×업종 단위로 잡아야 하는 근거를 만든다.

실행: python scripts/explore_external.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balgil.data import PROCESSED_DIR
from balgil.features import STAY_STORE_MID, resident_only

pd.set_option("display.width", 240)

# 체류형 중분류는 features.py로 옮겼다(C2). 식사·장보기 중분류는 여기서만 쓴다.
STAY_MID = STAY_STORE_MID
MEAL_MID = ["한식", "중식", "일식", "서양식", "기타 간이", "구내식당·뷔페", "동남아시아", "기타 외국"]
GROC_MID = ["종합 소매", "식료품 소매", "음료 소매", "담배 소매"]
OLD_PATTERN = "음식|주점|커피|체육|여가|미용|스포츠"  # 고치기 전 features.py가 쓰던 것

STAY_MCT = [  # 카드 업종 기준 체류형
    "커피전문점", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지", "노래방",
    "유흥업소", "스포츠시설", "헬스장", "실내/실외골프장", "학원/학습지",
]
SGGS = ["서울 강남구", "강원 춘천시"]
MONTHS = ["07", "08", "09", "10", "11", "12"]


def elderly_population() -> pd.DataFrame:
    """행정동별 60세 이상 인구. 터전 지표의 분모."""
    h = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    return (
        h[h["연령대"].isin(["60대", "70대이상"])]
        .groupby(["ADM_CD", "ADM_NM", "SGG_NM"], as_index=False)["인구수"]
        .sum()
    )


def audit_resolution() -> None:
    print("■ 1. 외부 데이터 해상도 점검 — 동 단위로 떨어지는가\n")
    rows = []

    store = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet")
    rows.append(("소상공인 상가정보", f"{len(store):,}개", "행정동 (좌표 조인)", "터전", "O"))

    h = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    rows.append(("행안부 1인세대·인구", f"{len(h)}행", f"행정동 {h['ADM_CD'].nunique()}개 × 성 × 연령 5구간", "터전·라벨", "O"))

    for name, path, where in [
        ("복지로 중앙부처", "res_welfare_central.parquet", None),
        ("복지로 지자체", "res_welfare_local.parquet", "시군구"),
        ("1365 봉사 일감", "res_volunteer_target.parquet", "시군구"),
    ]:
        d = pd.read_parquet(PROCESSED_DIR / path)
        rows.append((name, f"{len(d)}건", where or "전국 (지역 구분 없음)", "자원 추천", "X"))

    df = pd.DataFrame(rows, columns=["데이터", "규모", "공간 해상도", "발길 어디에", "동 단위?"])
    print(df.to_string(index=False))
    print("\n  → 자원 3종은 모두 시군구 이상이다. 기획안 6절이 '어느 동에 무엇을 배치'를")
    print("     말하는데 자원 데이터가 동 단위가 아니다. 좌표가 있는 시설 표준데이터로 메워야 한다.\n")


def recount_stay_stores() -> pd.DataFrame:
    print("■ 2. 체류형 점포 재집계 — 패턴 버그 수정\n")
    s = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet")
    s["중"] = s["상권업종중분류명"].str.strip()

    new = s[s["중"].isin(STAY_MID)]
    old = s[s["중"].str.contains(OLD_PATTERN, na=False)]
    print(f"  새 정의 {len(new):,}개 / 기존 패턴 {len(old):,}개  (차이 {len(new) - len(old):,}개)")
    print(new["중"].value_counts().to_string())
    print("\n  기존 패턴은 '커피'로 찾았으나 상가정보 중분류명은 '비알코올 '이다.")
    print("  뒤쪽 공백까지 있어 strip() 없이는 isin()으로도 안 걸린다.\n")

    pop = elderly_population()
    cnt = new.groupby("ADM_CD").size().rename("체류점포")
    oldcnt = old.groupby("ADM_CD").size().rename("기존_관계형")
    m = pop.merge(cnt, on="ADM_CD", how="left").merge(oldcnt, on="ADM_CD", how="left").fillna(0)
    m["천명당"] = (m["체류점포"] / m["인구수"] * 1000).round(1)

    print("  기획안이 '관계형 점포 0개'로 인용한 북산면:")
    print(m[m["ADM_NM"] == "북산면"][["ADM_NM", "인구수", "기존_관계형", "체류점포", "천명당"]].to_string(index=False))
    zero = m[m["체류점포"] == 0]
    print(f"  체류형 점포가 실제로 0개인 동: {'없음' if zero.empty else ', '.join(zero['ADM_NM'])}")
    print("  → '0개'는 패턴이 만든 값이었다. 보고서에서 '20~200배 격차'로 바꿔야 한다.\n")

    for sgg in SGGS:
        d = m[m["SGG_NM"] == sgg].sort_values("천명당")
        cv = d["천명당"].std() / d["천명당"].mean()
        print(f"  [{sgg}] 60세+ 천 명당 체류형 점포 — 중위 {d['천명당'].median():.1f}, 변동계수 {cv:.2f}")
        print("    하위3:", ", ".join(f"{r.ADM_NM} {r.천명당}" for r in d.head(3).itertuples()))
        print("    상위3:", ", ".join(f"{r.ADM_NM} {r.천명당}" for r in d.tail(3).itertuples()))
    print("  → 강남 개포1동(1.4)이 춘천 농촌(8.2)보다 낮다. 터전 사막은 도시에도 있다.\n")
    return m


def seasonality() -> None:
    print("■ 3. 계절성 — 공통 충격 보정이 겨울에도 성립하는가\n")
    card = resident_only(pd.read_parquet(PROCESSED_DIR / "card_resid.parquet"))
    card = card[~card["IS_CORP"]].copy()
    card["YM"] = card["TA_YMD"].dt.strftime("%m")
    stay = card[card["MCT_RY_CD"].isin(STAY_MCT)]

    print("  체류 결제건수 월별 지수 (7월=100)")
    for sgg in SGGS:
        rows = []
        for age in ["30대", "50대", "70대", "80대"]:
            s = stay[(stay["MCT_SGG_CD"] == sgg) & (stay["AGE_CCD"] == age)].groupby("YM")["USE_CNT"].sum()
            rows.append({"연령": age, **{f"{m}월": round(s.get(m, 0) / s["07"] * 100, 1) for m in MONTHS}})
        d = pd.DataFrame(rows).set_index("연령")
        print(f"\n    [{sgg.split()[1]}]")
        print(d.to_string())
    print("\n  → 춘천은 30·50대가 12월에 -13/-9%인데 70대는 +24%다. 방향이 반대다.\n")

    print("  춘천 70대 체류 업종별 월별 지수 (7월=100) — 반대 방향의 정체")
    a = stay[(stay["MCT_SGG_CD"] == "강원 춘천시") & (stay["AGE_CCD"] == "70대")]
    p = a.pivot_table(index="MCT_RY_CD", columns="YM", values="USE_CNT", aggfunc="sum").fillna(0)
    p = p[p["07"] > 0]
    idx = (p.div(p["07"], axis=0) * 100).round(0)
    idx["7월건수"] = p["07"].astype(int)
    print(idx.sort_values("7월건수", ascending=False).to_string())
    print("\n  → 목욕탕 270(2.7배), 노래방 241, 스포츠시설 202 상승 / 골프장 53으로 반토막.")
    print("     같은 기온이 업종별로 반대 방향으로 작용한다. 연령별 업종 구성이 다르므로")
    print("     '전 연령이 함께 떨어진 만큼 제거'하는 보정은 겨울에 성립하지 않는다.")
    print("     보정 기준선을 연령×업종 단위로 잡고, 기온을 설명변수로 넣어야 한다.")


def main() -> None:
    audit_resolution()
    recount_stay_stores()
    seasonality()


if __name__ == "__main__":
    main()
