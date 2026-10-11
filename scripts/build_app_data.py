"""화면(D3)이 읽는 작은 파일을 만든다 → data/reference/app/ (git에 올린다).

화면은 원본(SGIS 경계 135MB, 상가정보 364MB)을 직접 읽지 않는다. 여기서 47개 동만 잘라
가볍게 만든 결과를 올려 두면, 원본이 없는 팀원도 `streamlit run app/balgil_app.py`로 화면을 띄울 수 있다.

산출
  dong_map.geojson   47개 동 경계(단순화, WGS84) + 터전 지표
                     터전점수_통신·순위(A4), 60세+ 천 명당 체류형 점포(C2)·경로당·도서관(C3)
  facilities.csv     경로당·마을회관·도서관 591곳 좌표 (C3)
  shap_weekly.csv    좁아짐 분류 모델(재분석 b3, 랜덤포레스트)의 집단×주 SHAP 값과 예측 확률

선행: build_spatial.py → build_dong_panel.py → build_facility.py
      (SHAP은 git에 있는 reanalysis/reference/weekly_panel.csv만 쓴다)
실행: python scripts/build_app_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402
from balgil.features import is_stay_store  # noqa: E402
from build_spatial import load_dong  # noqa: E402

OUT = ROOT / "data" / "reference" / "app"
REF = ROOT / "reanalysis" / "reference"
SIMPLIFY_M = 30  # 경계 단순화 허용 오차(m). 화면 축척에서 티가 나지 않고 파일이 작아진다

# 재분석 b3_models.py 모델 ①과 같은 변수·설정 (90대 제외 32칸, y가 있는 주만)
FEATURES = ["breadth_z", "stay_z", "narrow", "d_narrow", "d_stay_z", "d_breadth_z", "m3", "meal", "anon", "med", "evening"]


def dong_map() -> None:
    dong = load_dong()
    panel = pd.read_parquet(PROCESSED_DIR / "features_dong.parquet")
    fac = pd.read_parquet(PROCESSED_DIR / "fac_dong.parquet")[["ADM_CD", "경로당수", "도서관수"]]
    store = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet")
    stay = store[is_stay_store(store)].groupby("ADM_CD").size().rename("체류형점포수")
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    pop = hh[hh["연령대"].isin(["60대", "70대이상"])].groupby("ADM_CD")["인구수"].sum().rename("인구_60세이상")

    keep = ["ADM_CD", "도시", "터전점수_통신", "터전순위_통신", "60대이상_비중", "저녁비중", "일요일_평일비", "겨울유지"]
    g = (
        dong[["ADM_CD", "ADM_NM", "SGG_NM", "geometry"]]
        .merge(panel[keep], on="ADM_CD", how="left")
        .merge(fac, on="ADM_CD", how="left")
        .merge(stay, on="ADM_CD", how="left")
        .merge(pop, on="ADM_CD", how="left")
    )
    g["체류형점포수"] = g["체류형점포수"].fillna(0).astype(int)
    per = g["인구_60세이상"] / 1000
    g["체류형점포_천명당"] = (g["체류형점포수"] / per).round(1)
    g["경로당_천명당"] = (g["경로당수"] / per).round(2)
    g["도서관_천명당"] = (g["도서관수"] / per).round(2)
    g["geometry"] = g.geometry.simplify(SIMPLIFY_M)
    g = g.to_crs("EPSG:4326")
    g.to_file(OUT / "dong_map.geojson", driver="GeoJSON")
    print(f"dong_map.geojson: {len(g)}개 동, {(OUT / 'dong_map.geojson').stat().st_size / 1e3:.0f} KB")


def facilities() -> None:
    f = pd.read_parquet(PROCESSED_DIR / "fac_adm.parquet")
    f = f[["SGG_NM", "ADM_CD", "ADM_NM", "시설종류", "세부유형", "시설명", "위도", "경도"]]
    f.to_csv(OUT / "facilities.csv", index=False, encoding="utf-8-sig")
    print(f"facilities.csv: {len(f)}곳 {f['시설종류'].value_counts().to_dict()}")


def shap_weekly() -> None:
    import shap
    from sklearn.ensemble import RandomForestClassifier

    p = pd.read_csv(REF / "weekly_panel.csv")
    d = p.dropna(subset=["y"]).copy()
    d["y"] = d["y"].astype(int)
    rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=0)
    rf.fit(d[FEATURES], d["y"])
    sv = shap.TreeExplainer(rf).shap_values(d[FEATURES])
    sv = sv[:, :, 1] if sv.ndim == 3 else sv[1]  # 양성(다음 주 좁아짐 상위 진입) 쪽
    out = d[["seg", "city", "sex", "AGE", "w", "y"]].reset_index(drop=True)
    out["확률"] = rf.predict_proba(d[FEATURES])[:, 1].round(4)
    out = pd.concat([out, pd.DataFrame(sv, columns=FEATURES).round(4)], axis=1)
    out.to_csv(OUT / "shap_weekly.csv", index=False, encoding="utf-8-sig")
    print(f"shap_weekly.csv: {len(out)}행 (집단 {out['seg'].nunique()} × 주 {out['w'].nunique()})")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dong_map()
    facilities()
    shap_weekly()


if __name__ == "__main__":
    main()
