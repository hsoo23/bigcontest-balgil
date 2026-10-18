"""#88 — 기준일까지의 데이터만 쓰면 끊김·좁아짐 판정이 얼마나 바뀌나 (대조 실험, 저장소 판정은 그대로).

지금 판정(reanalysis/b2_continuity.py, agent.py)은 6개월을 다 본 사후 값이다.
  끊김 기준선   앞뒤 4주 같은 요일 중앙값 (b0_common.base)
  평소 흔들림   6개월 정상일 전체의 강건 표준편차
  좁아짐 순위   7~12월 6개월 평균 (narrow_cells)
  카드 양·질    기준일이 든 달 전체 (rate_state)
운영에서 쓸 수 있는 값으로 바꿔 다시 매기고 맞댄다.
  끊김 기준선   지난 8주 같은 요일 중앙값 (공휴일 빼고 3개 이상)
  평소 흔들림   그날 전까지 쌓인 정상일(28일 이상)의 강건 표준편차
  좁아짐 순위   7/1~기준일
  카드 양·질    그달 1일~기준일
나머지(7일 합, 같은 도시 30·40대 차감, 3배 기준, 빨강·주황 규칙)는 b2와 같다.
「과거만」은 기록이 쌓여야 판정할 수 있어 8/26부터 맞댄다.

선행: python reanalysis/a0_load_clean.py → python reanalysis/b2_continuity.py (원본이 있는 PC)
실행: python scripts/explore_causal_check.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reanalysis"))
warnings.filterwarnings("ignore")  # b2와 같다 — pandas·numpy 경고가 출력을 덮는다

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from b0_common import DAYS, ESS, HOL, MEAL, OUT, STAY, adjust, faces, load  # noqa: E402

AS_OF = pd.Timestamp("2025-10-12")  # 시연 기준일 (수치표 6-3)
CHECK_DAYS = ["2025-10-12", "2025-10-19", "2025-10-01"]  # 시연 주 · 다음 주 · 보조 장면
PAST_WEEKS = 8
MIN_NORMAL_DAYS = 28
SEV = {"빨강": 2, "주황": 1, "-": 0}


def roll(s: pd.Series) -> pd.Series:
    return s.rolling(7, min_periods=7).sum()


def base_past(s: pd.Series, k: int = PAST_WEEKS) -> pd.Series:
    """지난 k주 같은 요일 중앙값(공휴일 제외). b0_common.base의 앞뒤를 지난 쪽만으로."""
    ok = s[~s.index.isin(HOL)]
    out = {}
    for d in s.index:
        v = [ok[x] for x in (d - pd.Timedelta(days=7 * i) for i in range(1, k + 1)) if x in ok.index]
        out[d] = np.median(v) if len(v) >= 3 else np.nan
    return pd.Series(out)


def zs_past(x: pd.Series, normal: pd.Series) -> pd.Series:
    """그날 전까지의 정상일로만 잰 강건 z. b2_continuity.zs의 6개월 전체를 지난 쪽만으로."""
    out = pd.Series(np.nan, index=x.index)
    for d in x.index:
        n = x[(x.index < d) & normal].dropna()
        if len(n) >= MIN_NORMAL_DAYS:
            out[d] = (x[d] - n.median()) / (1.4826 * (n - n.median()).abs().median())
    return out


def breaks_past(r: pd.DataFrame) -> pd.DataFrame:
    r = r.assign(kind=np.where(r.ind.isin(STAY + MEAL), "대면", np.where(r.ind.isin(ESS), "필수", "기타")),
                 band=r.AGE.map({"30대": "3040", "40대": "3040", "60대": "60대", "70대": "70대", "80대": "80대"})).dropna(subset=["band"])
    normal = ~pd.Series(DAYS, index=DAYS).isin(HOL) & ~pd.Series(DAYS, index=DAYS).isin(pd.date_range("2025-10-03", "2025-10-15"))
    daily = lambda q: q.groupby("date").cnt.sum().reindex(DAYS).fillna(0)
    rows = []
    for c in ["춘천", "강남"]:
        ref = {k: daily(r[(r.city == c) & (r.band == "3040") & (r.kind == k)]) for k in ["대면", "필수"]}
        refd = {k: np.log(roll(ref[k]) / roll(base_past(ref[k]))) for k in ref}
        for sx in ["남성", "여성"]:
            for b in ["60대", "70대", "80대"]:
                z = {k: zs_past(np.log(roll(s) / roll(base_past(s))) - refd[k], normal)
                     for k in ["대면", "필수"] for s in [daily(r[(r.city == c) & (r.sex == sx) & (r.band == b) & (r.kind == k)])]}
                rows.append(pd.DataFrame({"date": DAYS, "seg": f"{c} {sx[0]} {b}", "f_z2": z["대면"].values, "e_z2": z["필수"].values}))
    p = pd.concat(rows, ignore_index=True)
    p["state"] = np.where(p.e_z2 <= -3, "빨강", np.where(p.f_z2 <= -3, "주황", "-"))
    p.loc[p.f_z2.isna() | p.e_z2.isna(), "state"] = np.nan
    return p


def week_state(d: pd.DataFrame, seg: str, as_of: pd.Timestamp) -> str:
    st = d[(d.seg == seg) & d.date.between(as_of - pd.Timedelta(days=6), as_of)].state.dropna()
    return max(st, key=SEV.get) if len(st) else "-"


def top7(f: pd.DataFrame) -> list[str]:
    f = f.assign(seg=f.city + " " + f.sex + " " + f.AGE)
    return f[f.AGE != "90대"].sort_values("narrow", ascending=False).head(7).seg.tolist()  # agent.py처럼 36칸에서 보정한 뒤 90대를 뺀다


def main() -> None:
    r, d1 = load()
    past = breaks_past(r)
    now = pd.read_csv(OUT / "break_daily.csv", encoding="utf-8-sig", parse_dates=["date"])
    now["state"] = now.state.map({"빨강(필수까지 끊김)": "빨강", "주황(대면만 끊김)": "주황"}).fillna("-")

    segs = sorted(past.seg.unique())
    first = past.dropna(subset=["state"]).date.min()
    sundays = pd.date_range(first + pd.Timedelta(days=6), DAYS.max(), freq="W-SUN")
    cmp = pd.DataFrame([(a, s, week_state(now, s, a), week_state(past, s, a)) for a in sundays for s in segs],
                       columns=["기준일", "집단", "지금", "과거만"])
    print(f"■ 끊김 — 과거만 판정이 되는 첫날 {first:%m/%d}부터, 일요일 {len(sundays)}주 × 12집단 = {len(cmp)}칸 (행 = 지금, 열 = 과거만)")
    print(pd.crosstab(cmp.지금 != "-", cmp.과거만 != "-", margins=True).to_string())
    print(f"  끊김 여부 일치 {((cmp.지금 != '-') == (cmp.과거만 != '-')).mean():.1%} · 색까지 일치 {(cmp.지금 == cmp.과거만).mean():.1%}")
    for a in map(pd.Timestamp, CHECK_DAYS):
        t = pd.DataFrame([(s, week_state(now, s, a), week_state(past, s, a)) for s in segs], columns=["집단", "지금", "과거만"])
        n = lambda col, v: int((t[col] == v).sum())
        print(f"  기준일 {a:%m/%d}: 지금 빨강 {n('지금', '빨강')} · 주황 {n('지금', '주황')} → 과거만 빨강 {n('과거만', '빨강')} · 주황 {n('과거만', '주황')}"
              + "".join(f" | {q.집단} {q.지금}→{q.과거만}" for q in t[t.지금 != t.과거만].itertuples()))

    k = ["city", "sex", "AGE"]
    full = adjust(faces(r, d1, k))
    upto = adjust(faces(r[r.date <= AS_OF], d1[d1.date <= AS_OF], k))
    tf, tp = top7(full), top7(upto)
    print(f"■ 좁아짐 상위 7칸 (90대 뺀 32칸) — 6개월 ↔ {AS_OF:%m/%d}까지: 겹침 {len(set(tf) & set(tp))} / 7")
    print("  6개월    :", " · ".join(tf))
    print(f"  {AS_OF:%m/%d}까지 :", " · ".join(tp))

    cw = r[(r.city == "춘천") & (r.sex == "여성") & r.AGE.isin(["50대", "70대"])]
    dw = d1[(d1.city == "춘천") & (d1.sex == "여성") & d1.AGE.isin(["50대", "70대"])]
    for name, lo, hi in [("10월 한 달", "2025-10-01", "2025-10-31"), (f"10/01~{AS_OF:%m/%d}", "2025-10-01", AS_OF)]:
        f = faces(cw[cw.date.between(lo, hi)], dw[dw.date.between(lo, hi)], k).reset_index()
        a70, a50 = f[f.AGE == "70대"].iloc[0], f[f.AGE == "50대"].iloc[0]
        print(f"■ 춘천 여 70대 카드 {name}: 양 {a70.breadth:.1f} (50대 {a50.breadth:.1f}, {a70.breadth / a50.breadth:.0%})"
              f" · 질 {a70.stay:.1f}% (50대 {a50.stay:.1f}%, {a70.stay / a50.stay:.0%})")


if __name__ == "__main__":
    main()
