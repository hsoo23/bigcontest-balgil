"""기획안 2절·12절(부록)이 인용하는 발길 수치를 다시 낸다.

옛 부록은 scripts/explore_signals.py의 「대면/익명 반복 비율」(성별을 섞은 옛 질 지표)을 썼다.
지금 지표는 재분석(reanalysis/b0_common.py) 정의 — 양 = 유효 발길 수 1/Σp², 질 = 체류 비중 — 이고,
연속성은 b2_continuity.py와 같은 7일 묶음 · 계절 보정 · 같은 도시 30·40대 차감이다.

  1·2·3절 (양·질·청년 구성): reanalysis/reference/features_segment.csv만 읽는다 — 원본 없이 돈다
  4절 (터전 통신 지표 퍼짐): data/processed/features_dong.parquet (python scripts/build_dong_panel.py)
  5·6절 (연속성 흔들림 · 추석): 카드 원본 정제본이 있어야 한다 (python reanalysis/a0_load_clean.py)

실행: python scripts/explore_plan_appendix.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reanalysis"))

AGES = ["20대", "50대", "60대", "70대", "80대"]
SEGS = [("춘천", "남성"), ("춘천", "여성"), ("강남", "남성"), ("강남", "여성")]


def segment_tables() -> None:
    s = pd.read_csv(ROOT / "reanalysis" / "reference" / "features_segment.csv")
    s = s.set_index(["city", "sex", "AGE"])
    for col, name, fmt in [("breadth", "1. 양 — 유효 발길 수", "{:.1f}"), ("stay", "2. 질 — 체류 비중 %", "{:.1f}")]:
        print(f"■ {name} (7~12월, 성×연령 칸)")
        t = pd.DataFrame({f"{c} {x}": [s.loc[(c, x, a), col] for a in AGES] for c, x in SEGS}, index=AGES).T
        ratio = (t["80대"] / t["50대"]).map("{:.2f}".format)
        t = t.map(fmt.format)
        t["80대÷50대"] = ratio
        print(t.to_string(), "\n")
    print("■ 3. 20대 칸의 구성 — 익명 비중 · 저녁(18~05시) 비중 %")
    rows = [("춘천", "남성", a) for a in ("20대", "50대", "80대")] + [("강남", "남성", a) for a in ("20대", "50대")]
    print(s.loc[rows, ["breadth", "stay", "anon", "evening", "breadth_z", "stay_z"]].round(2).to_string(), "\n")


def dong_spread() -> None:
    p = ROOT / "data" / "processed" / "features_dong.parquet"
    if not p.exists():
        print("■ 4. (건너뜀) features_dong.parquet 없음 — python scripts/build_dong_panel.py\n")
        return
    d = pd.read_parquet(p)
    print("■ 4. 통신 터전 지표 — 동 간 변동계수 (최소~최대)")
    for c in ["60대이상_비중", "저녁비중", "일요일_평일비", "겨울유지"]:
        g = d.groupby("도시")[c]
        lo, hi = d.loc[g.idxmin()], d.loc[g.idxmax()]
        cell = {k: f"{g.std()[k] / g.mean()[k]:.2f} ({lo.set_index('도시').loc[k, 'ADM_NM']} {g.min()[k]:.3f} ~ {hi.set_index('도시').loc[k, 'ADM_NM']} {g.max()[k]:.3f})" for k in g.std().index}
        print(f"  {c:10s}", " | ".join(f"{k} {v}" for k, v in cell.items()))
    print()


def continuity() -> None:
    try:
        from b0_common import DAYS, ESS, MEAL, STAY, base, load
        r, _ = load()
    except FileNotFoundError:
        print("■ 5·6. (건너뜀) 카드 정제본 없음 — python reanalysis/a0_load_clean.py (원본이 있는 PC)\n")
        return
    r["kind"] = np.where(r.ind.isin(STAY + MEAL), "대면", np.where(r.ind.isin(ESS), "필수", "기타"))
    roll = lambda x: x.rolling(7, min_periods=7).sum()  # noqa: E731
    daily = lambda m, k: r[m & (r.kind == k)].groupby("date").cnt.sum().reindex(DAYS).fillna(0)  # noqa: E731

    print("■ 5. 연속성 — 대면 발길 7일 묶음의 평소 흔들림 (계절 보정 · 30·40대 차감 뒤 로그 편차의 강건 표준편차, b2와 같은 방법)")
    out = {}
    for c, x in SEGS:
        ref = np.log(roll(daily((r.city == c) & r.AGE.isin(["30대", "40대"]), "대면")) / roll(base(daily((r.city == c) & r.AGE.isin(["30대", "40대"]), "대면"))))
        row = {}
        for a in ["60대", "70대", "80대", "90대"]:
            s = daily((r.city == c) & (r.sex == x) & (r.AGE == a), "대면")
            dv = (np.log(roll(s) / roll(base(s))) - ref).dropna()
            row[a] = 1.4826 * (dv - dv.median()).abs().median()
        out[f"{c} {x}"] = row
    t = pd.DataFrame(out).T
    t["90대÷80대"] = t["90대"] / t["80대"]
    print(t.round(3).to_string(), "\n")

    print("■ 6. 추석 — 춘천 70대 이상 하루 결제 ÷ 평소(앞뒤 4주 같은 요일 중앙값, 공휴일 제외)")
    s = r[(r.city == "춘천") & r.AGE.isin(["70대", "80대", "90대"])].groupby("date").cnt.sum().reindex(DAYS).fillna(0)
    b = base(s)
    print("  " + " · ".join(f"{d[5:]} {s[d] / b[d]:.2f}" for d in ["2025-10-06", "2025-10-07", "2025-10-08"]))


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    segment_tables()
    dong_spread()
    continuity()
