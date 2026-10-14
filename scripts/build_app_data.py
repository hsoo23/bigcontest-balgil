"""화면(D3)이 읽는 작은 파일을 만든다 → data/reference/app/ (git에 올린다).

화면은 원본(SGIS 경계 135MB, 상가정보 364MB)을 직접 읽지 않는다. 여기서 47개 동만 잘라
가볍게 만든 결과를 올려 두면, 원본이 없는 팀원도 `streamlit run app/balgil_app.py`로 화면을 띄울 수 있다.

산출
  dong_map.geojson   47개 동 경계(단순화, WGS84) + 터전 지표
                     터전 표(build_ground.py — 통신 A4, 상가 C2, 시설 C3)와 같은 값
  facilities.csv     경로당·마을회관·도서관 591곳 좌표 (C3)
  shap_weekly.csv    좁아짐 분류 모델(재분석 b3, 랜덤포레스트)의 집단×주 SHAP 값과 예측 확률
  agent_summary.csv  D1 agent.py briefing_tables()를 매주 일요일 기준으로 돌린 요약 (화면 ①)
  agent_groups.csv   같은 표의 12집단 × 주 신호·끊김 종류·상대방 업종 (화면 ①)
                     상대방 업종은 segment_industry(git 제외)가 있어야 채워진다 → 원본이 있는 PC에서 만든다

선행: build_spatial.py → build_dong_panel.py → build_facility.py (터전 값은 build_ground.build()를 그대로 쓴다),
      agent 표는 build_segment_industry.py
      SHAP은 reanalysis/a0_load_clean.py 산출(card*.pkl)로 b3 패널을 반올림 없이 다시 만들어 쓴다
실행: python scripts/build_app_data.py [--only map|shap|agent]  (requirements.txt 고정 버전: scikit-learn 1.7.2, shap 0.48.0)
주의: 같은 버전이어도 macOS arm64에서는 b3 랜덤포레스트가 reference/model_score.csv와 조금 다르게 나온다
      (칸 통째로 빼기 새 진입 16/31 ↔ 18/31). shap_weekly.csv는 reference를 만든 환경에서 만든다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from balgil.data import PROCESSED_DIR  # noqa: E402
from build_spatial import load_dong  # noqa: E402

OUT = ROOT / "data" / "reference" / "app"
REF = ROOT / "reanalysis" / "reference"
SIMPLIFY_M = 30  # 경계 단순화 허용 오차(m). 화면 축척에서 티가 나지 않고 파일이 작아진다

# 재분석 b3_models.py 모델 ①과 같은 변수·설정 (90대 제외 32칸, y가 있는 주만)
FEATURES = ["breadth_z", "stay_z", "narrow", "d_narrow", "d_stay_z", "d_breadth_z", "m3", "meal", "anon", "med", "evening"]


def dong_map() -> None:
    from build_ground import build

    dong = load_dong()
    panel = pd.read_parquet(PROCESSED_DIR / "features_dong.parquet")
    keep = ["ADM_CD", "60대이상_비중", "저녁비중", "일요일_평일비", "겨울유지"]
    g = dong[["ADM_CD", "ADM_NM", "SGG_NM", "geometry"]].merge(
        build().drop(columns=["SGG_NM", "ADM_NM"]), on="ADM_CD", how="left").merge(panel[keep], on="ADM_CD", how="left")
    g["geometry"] = g.geometry.simplify(SIMPLIFY_M)
    g = g.to_crs("EPSG:4326")
    g.to_file(OUT / "dong_map.geojson", driver="GeoJSON")
    print(f"dong_map.geojson: {len(g)}개 동, {(OUT / 'dong_map.geojson').stat().st_size / 1e3:.0f} KB")


def facilities() -> None:
    f = pd.read_parquet(PROCESSED_DIR / "fac_adm.parquet")
    f = f[["SGG_NM", "ADM_CD", "ADM_NM", "시설종류", "세부유형", "시설명", "위도", "경도"]]
    f.to_csv(OUT / "facilities.csv", index=False, encoding="utf-8-sig")
    print(f"facilities.csv: {len(f)}곳 {f['시설종류'].value_counts().to_dict()}")


def weekly_panel() -> pd.DataFrame:
    """b3_models.py와 같은 주별 패널을 반올림 없이 다시 만든다.

    reference/weekly_panel.csv는 4자리로 반올림된 값이라, 그걸로 학습하면 b3의 모델과 나무가 갈라져
    SHAP 상위 6개 순서가 9% 칸에서 달라진다(PR #25 리뷰). 선행: reanalysis/a0_load_clean.py
    """
    sys.path.insert(0, str(ROOT / "reanalysis"))
    from b0_common import AGES, adjust, faces, load

    r, d1 = load()
    wk = lambda s: (s - pd.Timestamp("2025-06-30")).dt.days // 7  # noqa: E731
    r["w"], d1["w"] = wk(r.date), wk(d1.date)
    keep = [a for a in AGES if a != "90대"]
    r, d1 = r[r.AGE.isin(keep)], d1[d1.AGE.isin(keep)]
    rows = []
    for w in range(26):
        i = adjust(faces(r[r.w == w], d1[d1.w == w], ["city", "sex", "AGE"]))
        i["w"] = w
        rows.append(i)
    p = pd.concat(rows, ignore_index=True)
    p["seg"] = p.city + " " + p.sex + " " + p.AGE
    p["top"] = (p.groupby("w").narrow.rank(ascending=False) <= 7).astype(int)
    p = p.sort_values(["seg", "w"])
    for c in ["narrow", "stay_z", "breadth_z"]:
        p["d_" + c] = p.groupby("seg")[c].diff().fillna(0)
    p["m3"] = p.groupby("seg").narrow.transform(lambda x: x.rolling(3, min_periods=1).mean())
    p["y"] = p.groupby("seg").top.shift(-1)

    # 저장소의 reference와 같은 패널인지 확인한다 (반올림 자리까지)
    ref = pd.read_csv(REF / "weekly_panel.csv")
    gap = (p[FEATURES].round(4).reset_index(drop=True) - ref[FEATURES]).abs().max().max()
    assert gap < 1e-3, f"reference/weekly_panel.csv와 다른 패널입니다 (최대 차 {gap})"
    return p


def shap_weekly() -> None:
    import shap
    from sklearn.ensemble import RandomForestClassifier

    p = weekly_panel()
    d = p.dropna(subset=["y"]).copy()
    d["y"] = d["y"].astype(int)
    rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=0)
    rf.fit(d[FEATURES], d["y"])
    sv = shap.TreeExplainer(rf).shap_values(d[FEATURES], check_additivity=True)
    sv = sv[:, :, 1] if sv.ndim == 3 else sv[1]  # 양성(다음 주 좁아짐 상위 진입) 쪽
    out = d[["seg", "city", "sex", "AGE", "w", "y"]].reset_index(drop=True)
    out["확률"] = rf.predict_proba(d[FEATURES])[:, 1].round(4)
    out = pd.concat([out, pd.DataFrame(sv, columns=FEATURES).round(4)], axis=1)
    out.to_csv(OUT / "shap_weekly.csv", index=False, encoding="utf-8-sig")
    print(f"shap_weekly.csv: {len(out)}행 (집단 {out['seg'].nunique()} × 주 {out['w'].nunique()})")


def agent_weekly() -> None:
    """화면 ①의 주(월~일)와 agent.py의 7일 창이 같아지도록 일요일을 기준일로 잡는다.
    명부(D4)는 아직 없어 대상자 표(agent_people)는 만들지 않는다."""
    from balgil.agent import WINDOW_DAYS, briefing_tables, load_inputs

    inp = load_inputs()
    first, last = pd.Timestamp(inp.breaks["date"].min()), pd.Timestamp(inp.breaks["date"].max())
    # 지난주 비교가 되도록 첫 창 앞에 7일이 더 있어야 한다
    days = pd.date_range(first + pd.Timedelta(days=2 * WINDOW_DAYS - 1), last, freq="W-SUN")
    summary, groups = [], []
    for as_of in days:
        t = briefing_tables(inp, as_of)
        summary.append(t["agent_summary"])
        groups.append(t["agent_groups"])
    pd.concat(summary).to_csv(OUT / "agent_summary.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    g = pd.concat(groups)
    g.to_csv(OUT / "agent_groups.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    broken = g["상태"].str.startswith("끊김")
    filled = int((broken & ~g["상대방업종"].str.contains("표 없음")).sum())
    print(f"agent 표: 기준일 {len(days)}개 ({days[0]:%m/%d}~{days[-1]:%m/%d}), 집단×주 {len(g)}행, "
          f"상대방 업종 채운 끊김 {filled}/{int(broken.sum())}")
    if inp.industry is None:
        print("  [주의] segment_industry.parquet 없음 — 상대방 업종이 비었습니다. 원본이 있는 PC에서 다시 만드세요")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["map", "shap", "agent"],
                    help="map = 경계·시설만, shap = SHAP만 (공간 원본 없이 돌릴 때), agent = 화면 ① agent.py 표만")
    only = ap.parse_args().only
    OUT.mkdir(parents=True, exist_ok=True)
    if only in (None, "map"):
        dong_map()
        facilities()
    if only in (None, "shap"):
        shap_weekly()
    if only in (None, "agent"):
        agent_weekly()


if __name__ == "__main__":
    main()
