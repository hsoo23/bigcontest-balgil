"""기상(ASOS)을 끊김 판정·발길 예상과 결합해 본다 (B4).

세 가지를 한다.
  1. 결합 테이블: 일자 × 도시 기상 + 궂은 날 표시 → data/reference/weather_daily.csv (git에 올린다)
     모델·보정·화면이 원본 없이 같은 기상값을 쓰게 한다
  2. 끊김 알림이 궂은 날에 몰리는가: break_daily(재분석 b2)의 보정 단계별 알림을 궂은 날과 맞댄다
     공통 충격 보정(30·40대 대조)이 날씨를 이미 지우는지 본다 → 화면 ①의 "날씨 n건" 근거
  3. 발길 예상(b3 ②)에 기온·강수를 넣으면 나아지는가: 같은 분할·같은 모델에 기상 열만 더한다

궂은 날 기준 (기상청 특보 기준을 일자료로 옮긴 근사값 — 특보 발령 이력이 아니다)
  폭염  최고기온 33℃ 이상      (폭염주의보: 일 최고체감온도 33℃ 이상)
  한파  최저기온 -12℃ 이하     (한파주의보: 아침 최저기온 -12℃ 이하)
  큰비  일강수량 30mm 이상     (호우주의보는 3·12시간 누적이라 일자료로 못 옮긴다. 생활에 지장이 큰 비로 근사)
  대설  신적설 5cm 이상        (대설주의보: 24시간 신적설 5cm 이상. 춘천은 미관측이라 판정 못 함)

선행: build_weather.py, reanalysis/a0_load_clean.py (3번만)
실행: python scripts/explore_weather.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reanalysis"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402

OUT = ROOT / "data" / "reference" / "weather_daily.csv"
REF = ROOT / "reanalysis" / "reference"
CITY = {"서울 강남구": "강남", "강원 춘천시": "춘천"}
FLAGS = {
    "폭염": lambda w: w["최고기온"] >= 33,
    "한파": lambda w: w["최저기온"] <= -12,
    "큰비": lambda w: w["강수량"] >= 30,
    "대설": lambda w: w["신적설"] >= 5,
}


def weather_table() -> pd.DataFrame:
    w = pd.read_parquet(PROCESSED_DIR / "ext_weather.parquet")
    w["city"] = w["SGG_NM"].map(CITY)
    w["date"] = pd.to_datetime(w["일자"])
    for k, f in FLAGS.items():
        w[k] = f(w).fillna(False).astype(bool)
    w["궂은날"] = w[list(FLAGS)].any(axis=1)
    out = w[["city", "date", "평균기온", "최저기온", "최고기온", "강수량", "신적설", *FLAGS, "궂은날"]]
    print("■ 궂은 날 (184일 중)")
    print(out.groupby("city")[[*FLAGS, "궂은날"]].sum().to_string())
    return out


def alerts_on_bad_days(w: pd.DataFrame) -> None:
    """break_daily의 date는 7일 창의 끝날이다(b2: roll 7). 그래서 그날 하루가 아니라 창 7일 안의 궂은 날 수를 본다."""
    w7 = w.sort_values("date").set_index("date").groupby("city")[[*FLAGS, "궂은날"]].rolling(7, min_periods=7).sum()
    w7 = w7.reset_index().rename(columns={k: f"{k}_7일" for k in [*FLAGS, "궂은날"]})
    b = pd.read_csv(REF / "break_daily.csv", parse_dates=["date"])
    m = b.merge(w7, on=["city", "date"], how="left")
    assert m["궂은날_7일"].notna().all(), "기상이 없는 창이 있습니다"
    allw = m.drop_duplicates(["city", "date"])
    print(f"\n■ 끊김 알림(집단×7일 창)의 창 안 궂은 날 수 — 모든 창 평균 {allw['궂은날_7일'].mean():.2f}일, "
          f"큰비 {allw['큰비_7일'].mean():.2f}일")
    rows = []
    for col, name in [("al0", "보정 없음"), ("al1", "계절형 보정 뒤"), ("al2", "공통 충격 보정 뒤")]:
        a = m[m[col]]
        rows.append((name, len(a), round(a["궂은날_7일"].mean(), 2), round(a["큰비_7일"].mean(), 2),
                     round((a["궂은날_7일"] == 0).mean() * 100)))
    print(pd.DataFrame(rows, columns=["단계", "알림", "궂은 날(평균)", "큰비(평균)", "궂은 날 없는 창 %"]).to_string(index=False))
    final = m[m["state"] != "-"]
    print(f"\n  최종 끊김(주황·빨강) {len(final)}건 — 창 안에 큰비가 있었던 것 {int((final['큰비_7일'] > 0).sum())}건")
    print(final.groupby(["city", "date"]).agg(집단=("seg", "size"), 큰비=("큰비_7일", "first"),
                                              폭염=("폭염_7일", "first")).to_string())


def forecast_with_weather(w: pd.DataFrame) -> pd.DataFrame:
    from b0_common import DAYS, HOL, MEAL, STAY, load
    from sklearn.ensemble import GradientBoostingRegressor

    r, _ = load()
    r["band"] = r.AGE.where(r.AGE.isin(["60대", "70대", "80대"]))
    f = r[r.band.notna() & r.ind.isin(STAY + MEAL)]
    wx = w.set_index(["city", "date"])
    base_ff = ["b4", "l7", "l14", "r7", "dow", "hol", "dom"]
    wx_ff = ["평균기온", "강수량", "큰비"]
    rows = []
    for (c, sx, b), g in f.groupby(["city", "sex", "band"]):
        # b3_models.py ② 발길 예상과 같은 입력·분할·모델. 기상 열만 더한다
        s = g.groupby("date").cnt.sum().reindex(DAYS).fillna(0)
        X = pd.DataFrame({"y": s})
        X["b4"] = pd.concat([s.shift(7 * i) for i in range(1, 5)], axis=1).median(axis=1)
        X["l7"], X["l14"], X["r7"] = s.shift(7), s.shift(14), s.shift(1).rolling(7).mean()
        X["dow"], X["hol"], X["dom"] = X.index.dayofweek, X.index.isin(HOL).astype(int), X.index.day
        X = X.join(wx.loc[c, wx_ff].astype(float))
        X = X.dropna()
        tr, te = X[X.index < "2025-11-15"], X[X.index >= "2025-11-15"]
        nh = te.hol == 0
        mape = lambda p: ((te.y - p).abs() / te.y)[nh].mean() * 100  # noqa: E731
        gbr = lambda ff: GradientBoostingRegressor(  # noqa: E731
            n_estimators=200, max_depth=3, learning_rate=.05, random_state=0).fit(tr[ff], tr.y).predict(te[ff])
        rows.append((c, sx, b, mape(te.b4), mape(gbr(base_ff)), mape(gbr(base_ff + wx_ff))))
    fc = pd.DataFrame(rows, columns=["도시", "성별", "연령", "기준선 MAPE", "부스팅 MAPE", "부스팅+기상 MAPE"]).round(1)
    print("\n■ 발길 예상(11/15~12/31, 공휴일 제외) — b3 ②에 기상 열(평균기온·강수량·큰비)을 더했을 때")
    print(fc.to_string(index=False))
    med = fc[["기준선 MAPE", "부스팅 MAPE", "부스팅+기상 MAPE"]].median()
    print("중앙값 MAPE  기준선 %.1f / 부스팅 %.1f / 부스팅+기상 %.1f" % tuple(med))
    print("기상을 넣어 나아진 집단 %d/12" % (fc["부스팅+기상 MAPE"] < fc["부스팅 MAPE"]).sum())
    return fc


def main() -> None:
    w = weather_table()
    out = w.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(OUT, index=False, encoding="utf-8-sig", lineterminator="\n")
    print(f"저장: {OUT.relative_to(ROOT)} ({len(out)}행)")
    alerts_on_bad_days(w)
    if (PROCESSED_DIR / "reanalysis" / "card2.pkl").exists():
        forecast_with_weather(w)
    else:
        print("\n[발길 예상] card2.pkl 없음 — reanalysis/a0_load_clean.py를 먼저 돌리면 3번도 합니다")


if __name__ == "__main__":
    main()
