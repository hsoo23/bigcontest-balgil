"""시설 표준데이터 2종(경로당·도서관)의 좌표를 행정동에 연결하고 동별 시설 수를 센다 (C3).

자원 데이터(복지로·1365)는 시군구 이상이라 "어느 동에 무엇이 있나"를 말할 수 없다
(explore_external.py 1절). 좌표가 있는 시설 표준데이터로 터전의 동 단위 자원을 채운다.

원본: fetch_facility_api.py가 Open API로 받은 전국 CSV (파일 다운로드는 5만 건에서 잘린다)
  data/external/fac_senior_center/  전국마을회관및경로당표준데이터 (15114136)
  data/external/fac_library/        전국도서관표준데이터           (15013109)

사회복지시설은 뺐다. 전국사회복지시설표준데이터(15096296)는 파일 없이 한국사회보장정보원
API(sclWlfrFcltInfoInqirService2)만 제공하는데, 이 API는 좌표·주소·건물관리번호를 주지 않고
소관 시군구까지만 알려 준다. 강남만 좌표가 있는 구 자체 자료가 있으나, 두 도시의 터전을
다른 재료로 재게 되므로 쓰지 않는다. 보고서 한계에 적는다.

정제 규칙
  * 인코딩은 UTF-8을 먼저 시도하고 안 되면 cp949로 읽는다 (포털 파일마다 다르다)
  * 폐업 시설은 뺀다(휴업은 남긴다). 위도·경도가 뒤바뀐 행은 바로잡고,
    국내 좌표 범위를 벗어나거나 비어 있는 행은 버리고 목록을 출력한다
  * 대상 지역 필터는 주소가 아니라 경계 공간 조인으로 한다. 경계 밖 좌표는 자연히 빠진다

선행: build_spatial.py (dong_master와 같은 SGIS 경계를 쓴다)
실행: python scripts/build_facility.py
산출: data/processed/fac_adm.parquet  (시설 단위, ADM_CD 포함)
      data/processed/fac_dong.parquet (47개 동 × 시설 종류별 개수. 경로당수는 마을회관 포함, 마을회관수는 그 안의 수)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT
from build_spatial import load_dong

EXTERNAL_DIR = ROOT / "data" / "external"
SOURCES = {"fac_senior_center": "경로당", "fac_library": "도서관"}
# 파일 다운로드본은 한글 열 이름, Open API(fetch_facility_api.py)는 영문 약어 열 이름이다.
NAME_COLS = ["시설명", "도서관명", "경로당명", "flctNm", "lbrryNm"]
TYPE_COLS = ["시설구분", "시설종류명", "시설종류상세명", "시설유형", "도서관유형", "flctTyp", "lbrrySe"]
LAT_COLS = ["위도", "latitude", "lat"]
LON_COLS = ["경도", "longitude", "lot", "lon"]
STATUS_COLS = ["영업상태명", "busiCodNm"]
LAT_RANGE, LON_RANGE = (33.0, 39.0), (124.0, 132.0)  # 국내 좌표 범위


def _read(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"인코딩을 읽지 못했습니다: {path}")


def _first(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


def load_source(slug: str, kind: str) -> pd.DataFrame:
    files = sorted((EXTERNAL_DIR / slug).glob("*.csv"))
    if not files:
        print(f"[{kind}] 원본 없음: data/external/{slug}/*.csv — 건너뜁니다")
        return pd.DataFrame()
    raw = pd.concat([_read(p) for p in files], ignore_index=True)

    name, typ = _first(raw, NAME_COLS), _first(raw, TYPE_COLS)
    lat, lon, status = _first(raw, LAT_COLS), _first(raw, LON_COLS), _first(raw, STATUS_COLS)
    if None in (name, lat, lon):
        raise SystemExit(f"[{kind}] 시설명·위도·경도 열을 찾지 못했습니다. 실제 열: {list(raw.columns)}")

    out = pd.DataFrame({
        "시설종류": kind,
        "시설명": raw[name],
        "세부유형": raw[typ] if typ else pd.NA,
        "위도": pd.to_numeric(raw[lat], errors="coerce"),
        "경도": pd.to_numeric(raw[lon], errors="coerce"),
    })
    n_all = len(out)
    if status:
        closed = raw[status].eq("폐업")
        out = out[~closed]
        print(f"[{kind}] 폐업 {closed.sum():,}개 제외 (휴업은 남김)")

    # 위도·경도가 뒤바뀐 행은 바로잡고, 그래도 국내 범위 밖인 행은 버린다.
    # (경로당 표준데이터에 경도 칸에 위도 값이 그대로 들어간 행이 있다 — 강남 자곡·방죽1·은곡)
    swapped = out["위도"].between(*LON_RANGE) & out["경도"].between(*LAT_RANGE)
    out.loc[swapped, ["위도", "경도"]] = out.loc[swapped, ["경도", "위도"]].to_numpy()
    bad = ~(out["위도"].between(*LAT_RANGE) & out["경도"].between(*LON_RANGE))
    print(f"[{kind}] 전국 {n_all:,}개, 위경도 뒤바뀜 {swapped.sum():,}개 바로잡음, 좌표 오류·없음 {bad.sum():,}개 제외 "
          f"(세부유형 열: {typ or '없음'})")
    if bad.any():
        print(out.loc[bad, ["시설명", "위도", "경도"]].head(10).to_string(index=False))
    return out[~bad]


def main() -> None:
    dong = load_dong()
    frames = [load_source(slug, kind) for slug, kind in SOURCES.items()]
    fac = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    if fac.empty:
        raise SystemExit("시설 원본이 하나도 없습니다.")

    pts = gpd.GeoDataFrame(fac, geometry=gpd.points_from_xy(fac["경도"], fac["위도"]), crs="EPSG:4326").to_crs(dong.crs)
    sj = gpd.sjoin(pts, dong[["ADM_CD", "ADM_NM", "SGG_NM", "geometry"]], how="inner", predicate="within")
    sj = pd.DataFrame(sj.drop(columns=["geometry", "index_right"]))

    print(f"\n■ 대상 지역 안 시설 {len(sj):,}개")
    print(sj.groupby(["SGG_NM", "시설종류"]).size().unstack(fill_value=0).to_string())
    if sj["세부유형"].notna().any():
        print("\n■ 세부유형")
        print(sj.groupby(["시설종류", "세부유형"]).size().to_string())

    counts = sj.groupby(["ADM_CD", "시설종류"]).size().unstack(fill_value=0).add_suffix("수")
    # 경로당수는 마을회관을 포함한다(같은 표준데이터). 2단계 창구 종류를 가르려고 마을회관만 따로 센다(#26·#27)
    counts["마을회관수"] = sj[sj["세부유형"].eq("마을회관")].groupby("ADM_CD").size()
    by_dong = dong[["SGG_NM", "ADM_CD", "ADM_NM"]].merge(counts, on="ADM_CD", how="left").fillna(0)
    num = [c for c in by_dong.columns if c.endswith("수")]
    by_dong[num] = by_dong[num].astype(int)
    zero = by_dong[by_dong[num].sum(axis=1) == 0]
    print(f"\n■ 동 {len(by_dong)}개 중 시설이 하나도 없는 동 {len(zero)}개"
          + (f": {', '.join(zero['ADM_NM'])}" if len(zero) else ""))

    sj.to_parquet(PROCESSED_DIR / "fac_adm.parquet", index=False)
    by_dong.to_parquet(PROCESSED_DIR / "fac_dong.parquet", index=False)
    print("\n저장: data/processed/fac_adm.parquet, fac_dong.parquet")


if __name__ == "__main__":
    main()
