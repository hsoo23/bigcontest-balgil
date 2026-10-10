"""A4 동 지표 패널을 만든다 (47개 행정동, 통신 데이터로 재는 터전).

윤지 재분석 `reanalysis/b4_ground.py`의 계산을 SK 원본에서 바로 하도록 옮겼다(b4는 삭제, 원본은 git 이력 5042bf3).
b4가 읽던 `sk_dong.csv`·`sk_age.pkl`을 만드는 코드는 넘겨받지 못해서, 지표 정의는
윤지 결과(`reanalysis/reference/features_dong.csv`)와 47개 동이 모두 같아지도록 맞췄다.

동 기준은 현수의 `data/reference/dong_code.csv`(SGIS 2025년 2분기 경계)다.
SK 격자는 BLOCK_CD 앞 8자리로 동을 정하고, 개포3동만 옛 코드(11230740)를 경계 코드(11230511)로
바꾼다. 옛 코드 격자 517개가 dong_code.csv의 개포3동 격자 수와 같아서 좌표 연결과 결과가 같다.

지표 (6개월, 60대 이상 = SK 60GU)
  60대이상_규모   60대 이상 유동인구 6개월 합 ÷ 144. 상대 비교용 축척 — 절대 인원수로 읽지 말 것
                  (flow_age_pop에는 시간대 축이 없어 '시간당'이 아님. 순위·상관에만 쓰므로 상수와 무관)
  60대이상_비중   60대 이상 ÷ 전 연령
  60대이상_여성비중  60대 이상 중 여성
  일요일_평일비   일요일 ÷ 평일(월~금) 평균, 전 연령
  저녁비중       18~23시 ÷ 하루, 전 연령
  겨울유지       60대 이상 12월 ÷ 9월
  터전점수_통신   도시 안 순위 평균: 60대 이상 비중(높을수록), 저녁·일요일·겨울유지(낮을수록). 낮을수록 터전이 약하다
체류형 점포·경로당·1인세대는 현수 C3에서 이 패널에 붙인다.

선행: data/reference/dong_code.csv (track-c)
실행: python scripts/build_dong_panel.py
산출: data/processed/features_dong.parquet (47행)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR, load_sk  # noqa: E402

DONG_CODE = ROOT / "data" / "reference" / "dong_code.csv"
SK_OLD_CODE = {"11230740": "11230511"}  # 개포3동: SK 옛 코드 → SGIS 경계 코드
CITY = {"서울 강남구": "강남", "강원 춘천시": "춘천"}
OLD = ["MAN_FLOW_POP_CNT_60GU", "WMAN_FLOW_POP_CNT_60GU"]
WEEKDAY = ["FLOW_POP_CNT_MON", "FLOW_POP_CNT_TUS", "FLOW_POP_CNT_WED", "FLOW_POP_CNT_THU", "FLOW_POP_CNT_FRI"]
EVENING = [f"TMST_{h}" for h in range(18, 24)]
# (지표, 높을수록 터전이 강한가). 순위는 1 = 터전이 가장 약한 동
RANK_BY = [("60대이상_비중", False), ("저녁비중", True), ("일요일_평일비", True), ("겨울유지", True)]


def sk(kind: str) -> pd.DataFrame:
    df = load_sk(kind)[0]
    return df.assign(ADM_CD=df["BLOCK_CD"].str[:8].replace(SK_OLD_CODE))


def main() -> None:
    dong = pd.read_csv(DONG_CODE, dtype={"ADM_CD": str})[["SGG_NM", "ADM_CD", "ADM_NM"]]
    dong["도시"] = dong["SGG_NM"].map(CITY)

    age = sk("age")
    pop = [c for c in age.columns if "FLOW_POP" in c]
    age["old"] = age[OLD].sum(axis=1)
    age["tot"] = age[pop].sum(axis=1)
    g = age.groupby("ADM_CD")[["old", "tot", "WMAN_FLOW_POP_CNT_60GU"]].sum()
    month_old = age.groupby(["ADM_CD", "STD_YM"])["old"].sum().unstack()
    month_share = month_old / age.groupby(["ADM_CD", "STD_YM"])["tot"].sum().unstack()

    wk = sk("wkdy").groupby("ADM_CD")[WEEKDAY + ["FLOW_POP_CNT_SUN"]].sum()
    tm = sk("time").groupby("ADM_CD")[[f"TMST_{h:02d}" for h in range(24)]].sum()

    panel = dong.set_index("ADM_CD").join(pd.DataFrame({
        "60대이상_규모": g["old"] / 144,
        "60대이상_비중": g["old"] / g["tot"],
        "60대이상_여성비중": g["WMAN_FLOW_POP_CNT_60GU"] / g["old"],
        "일요일_평일비": wk["FLOW_POP_CNT_SUN"] / wk[WEEKDAY].mean(axis=1),
        "저녁비중": tm[EVENING].sum(axis=1) / tm.sum(axis=1),
        "겨울유지": month_old["202512"] / month_old["202509"],
    })).reset_index()

    for col, asc in RANK_BY:
        panel[f"R_{col}"] = panel.groupby("도시")[col].rank(ascending=asc)
    panel["터전점수_통신"] = panel[[f"R_{c}" for c, _ in RANK_BY]].mean(axis=1)
    panel["터전순위_통신"] = panel.groupby("도시")["터전점수_통신"].rank(method="first").astype(int)
    panel = panel.drop(columns=[f"R_{c}" for c, _ in RANK_BY]).sort_values(["도시", "터전순위_통신"])

    miss = int(panel.isna().sum().sum())
    print(f"동 {panel.groupby('도시').size().to_dict()} (기대 강남 22, 춘천 25), 결측 {miss}")
    assert len(panel) == 47 and miss == 0, "동 패널 검증 실패"
    panel.to_parquet(PROCESSED_DIR / "features_dong.parquet", index=False)
    print("저장: data/processed/features_dong.parquet\n")

    # 월별 안정성: 60대 이상 비중 순위가 달마다 유지되는가 (b4와 같은 검증)
    city_of = dong.set_index("ADM_CD")["도시"]
    for c in ["춘천", "강남"]:
        x = month_share[month_share.index.map(city_of) == c]
        rk = x.rank(ascending=False)
        cor = rk.corr(method="spearman").values[np.triu_indices(6, 1)]
        top5 = int((rk.loc[rk.mean(axis=1).nsmallest(5).index] <= 5).all(axis=1).sum())
        print(f"■ {c} {len(x)}개 동: 월별 순위 상관 최솟값 {cor.min():.3f}, 평균 {cor.mean():.3f}, "
              f"상위 5개 동 중 6개월 내내 5위 안 {top5}")

    print("\n■ 터전이 가장 약한 동 (통신 기준, 도시별 3개)")
    cols = ["도시", "ADM_NM", "60대이상_비중", "저녁비중", "일요일_평일비", "겨울유지", "터전순위_통신"]
    print(panel.groupby("도시").head(3)[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
