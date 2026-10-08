"""발길의 '질' 지표를 검증하고 교체 근거를 만든다.

기획안 「발길」은 발길을 양·질·연속성·터전 네 면으로 재는데, 그중 '질'은
처음에 **대면/익명 반복 비율**로 정의했다. 이 스크립트는 그 지표를 검증했고
결과적으로 **체류 비중**으로 교체해야 한다는 결론에 도달한 과정을 재현한다.

검증 순서
  1 월별 안정성        대면/익명 비율이 달마다 흔들리지 않는가
  2 분자/분모 분해      강남 80대 반등이 대면 상승인가 익명 하락인가
  3 업종별 기여         반등을 만드는 업종이 무엇인가
  4 3분할 재정의        대면을 '식사 조달'과 '관계 체류'로 쪼개면 어떻게 되는가  ← 핵심
  5 체류 비중 안정성
  6 업종 제외 민감도    업종을 하나씩 빼도 연령 순서가 유지되는가
  7 양·질 독립성        두 면을 나눈 이유가 서는가
  8 커피전문점 의존도    체류 지표가 한 업종에 쏠려 있지 않은가
  9 대리 라벨 가용성     분류기 라벨과 음성 대조가 가능한가
 10 36셀 내부 일관성    성별로 쪼개도 패턴이 유지되는가

실행: python scripts/explore_quality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balgil.data import PROCESSED_DIR
from balgil.features import resident_only

pd.set_option("display.width", 240)

# 처음 쓴 2분할. 대면 안에 성격이 다른 둘이 섞여 있었다(검증 4).
FACE = [
    "한식", "중식", "일식", "양식", "기타요식", "커피전문점", "제과점", "미용실", "미용서비스",
    "싸우나/목욕탕", "안마/마사지", "노래방", "유흥업소", "스포츠시설", "헬스장",
    "실내/실외골프장", "학원/학습지",
]
ANON = ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매", "패스트푸드"]

# 교체한 3분할.
MEAL = ["한식", "중식", "일식", "양식", "기타요식", "패스트푸드", "제과점"]  # 차려진 음식 = 조리 대체
STAY = [  # 머무르며 얼굴을 익히는 곳 = 발길의 질
    "커피전문점", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지", "노래방",
    "유흥업소", "스포츠시설", "헬스장", "실내/실외골프장", "학원/학습지",
]
GROC = ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매"]  # 직접 장보기

SGGS = ["서울 강남구", "강원 춘천시"]
AGES = ["20대", "30대", "40대", "50대", "60대", "70대", "80대"]
OLD = ["50대", "60대", "70대", "80대"]


def load_card() -> pd.DataFrame:
    """주민 결제만, 법인 제외. 방문객 패턴이 섞이면 생활 반경이 왜곡된다."""
    card = resident_only(pd.read_parquet(PROCESSED_DIR / "card_resid.parquet"))
    card = card[~card["IS_CORP"]].copy()
    card["YM"] = card["TA_YMD"].dt.strftime("%m")
    return card


def share(df: pd.DataFrame, mcts: list[str]) -> float:
    """해당 업종군이 전체 결제건수에서 차지하는 비중(%)."""
    counts = df.groupby("MCT_RY_CD")["USE_CNT"].sum()
    total = counts.sum()
    return counts[counts.index.isin(mcts)].sum() / total * 100 if total else np.nan


def ratio(df: pd.DataFrame, num: list[str], den: list[str]) -> float:
    counts = df.groupby("MCT_RY_CD")["USE_CNT"].sum()
    d = counts[counts.index.isin(den)].sum()
    return counts[counts.index.isin(num)].sum() / d if d else np.nan


def effective_breadth(df: pd.DataFrame) -> float:
    """유효 발길 수. 허핀달 지수의 역수 — 결제가 몇 개 업종에 진짜로 퍼져 있는가."""
    p = df.groupby("MCT_RY_CD")["USE_CNT"].sum()
    p = p / p.sum()
    return 1 / (p**2).sum()


def cells(card: pd.DataFrame, ages=AGES):
    for sgg in SGGS:
        for age in ages:
            yield sgg, age, card[(card["MCT_SGG_CD"] == sgg) & (card["AGE_CCD"] == age)]


def monthly_table(card, fn, ages=AGES) -> pd.DataFrame:
    rows = []
    for sgg, age, a in cells(card, ages):
        row = {"지역": sgg.split()[1], "연령": age}
        for ym, g in a.groupby("YM"):
            row[f"{ym}월"] = round(fn(g), 3)
        vals = [v for k, v in row.items() if k.endswith("월")]
        row["표준편차"] = round(float(np.std(vals, ddof=1)), 3)
        rows.append(row)
    return pd.DataFrame(rows).set_index(["지역", "연령"])


def main() -> None:
    card = load_card()

    print("■ 1. 대면/익명 비율 월별 안정성")
    print(monthly_table(card, lambda g: ratio(g, FACE, ANON)).to_string())
    print("  → 표준편차 0.009~0.024. 지표 자체는 안정적이고, 강남 80대 반등도 노이즈가 아니다.\n")

    print("■ 2. 분자/분모 분해 — 반등은 대면 상승인가 익명 하락인가")
    rows = [
        {
            "지역": sgg.split()[1], "연령": age,
            "대면%": round(share(a, FACE), 1), "익명%": round(share(a, ANON), 1),
            "비율": round(ratio(a, FACE, ANON), 3),
        }
        for sgg, age, a in cells(card, OLD)
    ]
    print(pd.DataFrame(rows).to_string(index=False))
    print("  → 강남 80대는 익명이 32.8%→29.7%로 빠지면서 비율이 올라갔다. 관계가 늘어난 것이 아니다.\n")

    print("■ 3. 강남 고령층 업종별 비중(%) — 반등을 만드는 업종")
    cols = []
    for age in OLD:
        a = card[(card["MCT_SGG_CD"] == "서울 강남구") & (card["AGE_CCD"] == age)]
        s = a.groupby("MCT_RY_CD")["USE_CNT"].sum()
        cols.append((s / s.sum() * 100).rename(age))
    g = pd.concat(cols, axis=1).fillna(0)
    g["변화_70to80"] = (g["80대"] - g["70대"]).round(2)
    watch = [m for m in FACE + ANON if m in g.index]
    print(g.loc[watch].round(2).sort_values("변화_70to80", ascending=False).to_string())
    print("  → 할인점 -2.79pp, 한식 +1.39pp. 장보기가 줄고 차려진 음식으로 옮겨간 것이다.\n")

    print("■ 4. 대면을 '식사 조달'과 '관계 체류'로 쪼개면  ← 교체 근거")
    rows = [
        {
            "지역": sgg.split()[1], "연령": age,
            "식사%": round(share(a, MEAL), 1), "체류%": round(share(a, STAY), 1),
            "장보기%": round(share(a, GROC), 1), "체류/장보기": round(ratio(a, STAY, GROC), 3),
        }
        for sgg, age, a in cells(card)
    ]
    print(pd.DataFrame(rows).to_string(index=False))
    print("  → 체류 비중은 두 지역 모두 예외 없이 단조 감소하고 80대 반등이 사라진다.")
    print("     식사 비중만 80대에서 반등한다(조리 대체). 질 지표는 체류 비중으로 교체한다.\n")

    print("■ 5. 체류 비중 월별 안정성")
    print(monthly_table(card, lambda g: share(g, STAY), ["20대"] + OLD).to_string())
    print()

    print("■ 6. 민감도 — 체류 업종을 하나씩 빼도 50>60>70>80이 유지되는가")
    broken = []
    for drop in STAY:
        sub = [m for m in STAY if m != drop]
        keeps = {}
        for sgg in SGGS:
            v = [share(card[(card["MCT_SGG_CD"] == sgg) & (card["AGE_CCD"] == a)], sub) for a in OLD]
            keeps[sgg] = all(v[i] > v[i + 1] for i in range(3))
        if not all(keeps.values()):
            broken.append((drop, keeps))
    print(f"  {len(STAY) - len(broken)}/{len(STAY)}개 업종에서 단조 감소 유지")
    for d, k in broken:
        print(f"  깨짐: {d} → {k}")
    print()

    print("■ 7. 양 · 질 독립성 (지역×연령 14개 셀)")
    pts = pd.DataFrame(
        [{"양": effective_breadth(a), "질": share(a, STAY)} for _, _, a in cells(card)]
    )
    print(f"  피어슨 r = {pts.corr().iloc[0, 1]:.3f} / 스피어만 r = {pts.corr(method='spearman').iloc[0, 1]:.3f}")
    print(f"  → r²={pts.corr().iloc[0, 1] ** 2:.2f}. 분산의 80% 이상을 서로 설명하지 못하므로 두 면을 나눈다.\n")

    print("■ 8. 커피전문점 의존도 — 체류 지표가 한 업종에 쏠려 있지 않은가")
    nocof = [m for m in STAY if m != "커피전문점"]
    rows = []
    for sgg, age, a in cells(card, ["20대"] + OLD):
        t, n = share(a, STAY), share(a, nocof)
        rows.append({"지역": sgg.split()[1], "연령": age, "체류%": round(t, 2),
                     "커피제외%": round(n, 2), "커피비중": f"{(t - n) / t * 100:.0f}%"})
    print(pd.DataFrame(rows).to_string(index=False))
    print("  → 강남은 체류의 75~86%가 커피 한 업종이다. 춘천은 40~65%로 분산되어 있다.")
    print("     지역별로 지표 신뢰도가 다르므로 교차검증 해석에 반영해야 한다.\n")

    print("■ 9. 대리 라벨 가용성 (분류기 라벨 + 음성 대조)")
    h = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    for age in ["70대이상", "60대", "40대", "30대"]:
        d = h[h["연령대"] == age].groupby(["SGG_NM", "ADM_NM"])["일인세대율"].mean() * 100
        q = d.quantile([0.2, 0.5, 0.8])
        print(f"  {age:6s} 하위20% {q[0.2]:5.1f}%  중위 {q[0.5]:5.1f}%  상위20% {q[0.8]:5.1f}%  범위 {d.min():.1f}~{d.max():.1f}")
    print("  → 라벨(70대이상 상·하위 20%)과 음성 대조(30·40대) 모두 가능하다.\n")

    print("■ 10. 36셀 내부 일관성 — 성별로 쪼개도 유지되는가")
    rows = []
    for sgg in SGGS:
        for sex in ["남성", "여성"]:
            a = card[(card["MCT_SGG_CD"] == sgg) & (card["SEX_CCD"] == sex)]
            row = {"지역": sgg.split()[1], "성별": sex}
            vals = []
            for age in AGES:
                v = share(a[a["AGE_CCD"] == age], STAY)
                row[age] = round(v, 2)
                vals.append(v)
            row["50→80"] = "유지" if all(vals[i] > vals[i + 1] for i in range(3, 6)) else "깨짐"
            rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))
    print("  → 4개 셀 모두 50대 이후 단조 감소. 20·30대 사이 역전은 청년 프로필의 특징이다.")


if __name__ == "__main__":
    main()
