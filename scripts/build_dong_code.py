"""47개 행정동 코드 대조표(dong_code.csv)를 만든다 (C1).

SGIS 행정동 경계를 기준으로 데이터마다 다른 동 식별자를 한 줄에 모은다.
  SGIS 경계   : ADM_CD 8자리 (11230510) + ADM_NM — 기준
  SK 유동인구 : BLOCK_CD 앞 8자리. 대부분 ADM_CD와 같고, 개편된 동은 좌표로 보완했다
  행안부      : 행정기관코드 10자리 (1168051000), 읍면동명으로 연결
  상가정보    : 행정동코드 8자리 (11680640), 점포 좌표 공간 조인으로 연결

동 이름이 "코드·좌표 추정"이라는 재분석 주의문과 "SGIS 100% 검증" 기록이 엇갈린다.
이 스크립트는 네 출처가 같은 동을 가리키는지 동마다 확인하고, 어긋난 곳을 비고에 남긴다.

선행: build_processed.py → build_external.py → build_spatial.py
실행: python scripts/build_dong_code.py
산출: data/processed/dong_code.csv (수경 A4 동 패널의 기준)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR

EXPECTED_DONG = {"서울 강남구": 22, "강원 춘천시": 25}
OUT = PROCESSED_DIR / "dong_code.csv"


def sk_codes() -> pd.DataFrame:
    """동별 SK 격자 수와, ADM_CD와 다른 BLOCK_CD 앞 8자리(행정동 개편 흔적)."""
    sk = pd.read_parquet(PROCESSED_DIR / "sk_cell_adm.parquet", columns=["BLOCK_CD", "ADM_CD"])
    sk["SK_CD"] = sk["BLOCK_CD"].str[:8]
    old = sk[sk["SK_CD"] != sk["ADM_CD"]].groupby("ADM_CD")["SK_CD"].agg(lambda s: ",".join(sorted(s.unique())))
    return pd.DataFrame({"SK_격자수": sk.groupby("ADM_CD").size(), "SK_옛코드": old}).reset_index()


def mois_codes() -> pd.DataFrame:
    """행안부 행정기관코드. build_spatial.link_mois()가 이름으로 붙인 ADM_CD를 쓴다."""
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet", columns=["ADM_CD", "읍면동명", "행정기관코드"])
    hh = hh.dropna(subset=["ADM_CD"]).drop_duplicates(["ADM_CD", "행정기관코드"])
    hh["행정기관코드"] = hh["행정기관코드"].astype("int64").astype(str)
    dup = hh[hh["ADM_CD"].duplicated(keep=False)]
    if not dup.empty:
        print(f"[행안부] 한 동에 행정기관코드가 둘 이상: {dup.to_dict('records')}")
    return hh.groupby("ADM_CD").agg(MOIS_CD=("행정기관코드", "first"), MOIS_NM=("읍면동명", "first")).reset_index()


def store_codes() -> pd.DataFrame:
    """상가정보 행정동코드. 좌표로 들어온 동에서 가장 많은 코드와 그 비율을 본다."""
    st = pd.read_parquet(PROCESSED_DIR / "store_adm.parquet", columns=["ADM_CD", "행정동코드", "행정동명"])
    top = st.groupby(["ADM_CD", "행정동코드", "행정동명"]).size().rename("n").reset_index()
    top["비율"] = top["n"] / top.groupby("ADM_CD")["n"].transform("sum")
    top = top.sort_values(["ADM_CD", "n"], ascending=[True, False]).drop_duplicates("ADM_CD")
    return top.rename(columns={"행정동코드": "STORE_CD", "행정동명": "STORE_NM", "n": "점포수", "비율": "STORE_일치율"})


def main() -> None:
    dong = pd.read_parquet(PROCESSED_DIR / "dong_master.parquet")[["SGG_NM", "ADM_CD", "ADM_NM"]]
    out = (
        dong.merge(sk_codes(), on="ADM_CD", how="left")
        .merge(mois_codes(), on="ADM_CD", how="left")
        .merge(store_codes(), on="ADM_CD", how="left")
        .sort_values(["SGG_NM", "ADM_CD"])
        .astype({"SK_격자수": "Int64", "점포수": "Int64"})
    )
    out["STORE_일치율"] = out["STORE_일치율"].round(3)

    notes = []
    for r in out.itertuples():
        n = []
        if pd.isna(r.SK_격자수):
            n.append("SK 격자 없음")
        if isinstance(r.SK_옛코드, str):
            n.append(f"SK 옛 코드 {r.SK_옛코드}를 좌표로 보완")
        if pd.isna(r.MOIS_CD):
            n.append("행안부 미매칭")
        if pd.isna(r.STORE_CD):
            n.append("상가 점포 없음")
        elif r.STORE_NM != r.ADM_NM:
            n.append(f"상가 행정동명 '{r.STORE_NM}'")
        elif r.STORE_일치율 < 0.95:
            n.append(f"상가 코드 일치율 {r.STORE_일치율:.0%}")
        notes.append("; ".join(n))
    out["비고"] = notes

    found = out.groupby("SGG_NM").size().to_dict()
    print(f"■ 행정동 {found} (기대값 {EXPECTED_DONG}) — {'일치' if found == EXPECTED_DONG else '불일치'}")
    print(f"  이름 중복(같은 시군구 안): {out.duplicated(['SGG_NM', 'ADM_NM']).sum()}개")
    for col, label in [("SK_격자수", "SK"), ("MOIS_CD", "행안부"), ("STORE_CD", "상가")]:
        print(f"  {label} 연결: {out[col].notna().sum()}/{len(out)}")
    flagged = out[out["비고"] != ""]
    print(f"\n■ 확인이 필요한 동 {len(flagged)}개")
    print(flagged[["SGG_NM", "ADM_CD", "ADM_NM", "비고"]].to_string(index=False) if len(flagged) else "  없음")

    cols = ["SGG_NM", "ADM_CD", "ADM_NM", "MOIS_CD", "STORE_CD", "SK_격자수", "점포수", "STORE_일치율", "비고"]
    out[cols].to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUT.relative_to(PROCESSED_DIR.parents[1])}")
    print("남은 일: SGIS 행정구역 코드표를 내려받아 ADM_CD·ADM_NM 47줄을 눈으로 대조하고 비고를 채운다.")


if __name__ == "__main__":
    main()
