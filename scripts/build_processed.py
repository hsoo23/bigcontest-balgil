"""원본 데이터를 정제해 data/processed/*.parquet로 저장하고 품질 리포트를 생성한다.

실행: python scripts/build_processed.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import CARD_FILES, PROCESSED_DIR, ROOT, SK_KINDS, load_card, load_sk

REPORT = ROOT / "reports" / "data_quality.md"


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    out = ["# 데이터 품질 리포트", "", "`scripts/build_processed.py` 실행 시 자동 생성됩니다.", ""]

    out += ["## SK 유동인구", ""]
    sk_stats = []
    for kind in SK_KINDS:
        df, st = load_sk(kind)
        df.to_parquet(PROCESSED_DIR / f"sk_{kind}.parquet", index=False)
        sk_stats.append(st)
        adm = df.groupby("SGG_NM")["ADM_CD"].nunique().to_dict()
        print(f"sk_{kind}: {len(df):,} rows, 행정동 수 {adm}")
    st = pd.concat(sk_stats)
    st[["rows_raw", "dup_removed", "outside_sgg", "rows_clean"]] = st[["rows_raw", "dup_removed", "outside_sgg", "rows_clean"]].astype(int)
    out += [md_table(st), ""]
    out += [
        "- `dup_removed`: 완전 중복 행 제거 수. 주최 측 공지대로 `flow_time_pop_202512`, `flow_wkdy_pop_202512`에서만 발생합니다.",
        "- `outside_sgg`: 강남구(11230)·춘천시(32010) 외 인접 시군구 격자로, 분석에서 제외했습니다.",
        "- 모든 값은 해당 월의 **일평균** 유동인구입니다(일자별 값은 제공되지 않음).",
        "",
    ]

    out += ["## 신한카드", ""]
    for name in CARD_FILES:
        df = load_card(name)
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
        smry = (
            df.groupby("MCT_SGG_CD")
            .agg(rows=("USE_CNT", "size"), corp_rows=("IS_CORP", "sum"), 결제액_억원=("TS_AT", "sum"), 결제건수=("USE_CNT", "sum"))
            .reset_index()
        )
        smry["결제액_억원"] = (smry["결제액_억원"] / 1e8).round(0).astype(int)
        smry[["rows", "corp_rows", "결제건수"]] = smry[["rows", "corp_rows", "결제건수"]].astype(int)
        out += [
            f"### {name} (`{CARD_FILES[name]}`)",
            "",
            f"- 행 수 {len(df):,}, 기간 {df.TA_YMD.min():%Y-%m-%d} ~ {df.TA_YMD.max():%Y-%m-%d} ({df.TA_YMD.nunique()}일), "
            f"업종 {df.MCT_RY_CD.nunique()}개, 결측 {int(df.isna().sum().sum())}건, 중복 {int(df.duplicated().sum())}건",
            f"- USE_CNT 최솟값 {df.USE_CNT.min()} → 결제 5건 미만 셀은 비식별 처리로 삭제된 것으로 보이며, 빈 셀은 0이 아닌 '소량'으로 해석해야 합니다.",
            "",
            md_table(smry),
            "",
        ]
        print(f"{name}: {len(df):,} rows")

    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"리포트 저장: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
