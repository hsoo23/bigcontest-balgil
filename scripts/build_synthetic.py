"""페르소나 가상 데이터(D4)를 만든다 — 돌봄 명부 41명과 발길이 닿던 곳 표. 둘 다 「가상」이다.

가상 데이터는 돌봄 명부에만 쓴다. 지표·모델·보고서 성능 수치에는 쓰지 않는다(기획안 8절).
생성 방식 설명은 docs/draft/E5_가상데이터설계자료.md (규정 필수 제출물). 이 파일과 그 문서가 같은 규칙을 적는다.

산출 (git에 올린다. 파일명·비고 열에 「가상」, 협업규칙 6절)
  data/synthetic/roster_가상.csv   돌봄 명부 41명 (docs/agent_입력형식.md 1절 형식 + 나이·비고)
  data/synthetic/places_가상.csv   발길이 닿던 곳 (2절 형식 + 비고). 경로당·마을회관은 실제 공공시설 위치,
                                    가게만 가상

규칙 요약 (근거는 E5 3절)
  1. 칸 인원: 명부 전체 41명, 12칸(시군구 × 성 × 연령대 60·70·80대). 시연 칸(춘천 여성 70대)만 8명(#20 (a), #35).
     나머지 33명은 11칸에 행안부 65~89세 1인세대수 비례로 나누되 칸마다 2~4명(#20 "칸당 3~4명" 근처).
  2. 나이·동: 칸 안에서 (행정동 × 1세 나이)를 행안부 1인세대수 비례로 뽑는다. 명부 사업(노인맞춤돌봄·기초연금)이
     65세 이상이라 60대 칸은 65~69세다. 장면 재현용으로 두 칸만 몇 명을 먼저 둔다(FIXED) — 시연 칸에 교동 2명
     (9절 "3명 중 2명이 교동"), 춘천 여성 80대 칸에 북산면 1명(터전 약한 순 1위, 경로당·마을회관 창구를 화면에 보이려고).
  3. 마지막접촉일: 2025-05-01 ~ 2025-07-19에서 고르게. 화면 ①의 가장 이른 기준일(07/20)보다 앞서야 한다(read_roster).
     FIXED로 둔 사람은 칸 안 오래된 순 자리도 정해 둔다(확인 권고 상위 3명 안에 들게). 손으로 정한 값은 이 셋뿐이다.
  4. 가게: 도시마다 고령 6집단의 상대방 업종(agent.counterpart_industries) 합집합 × 47동. 게이트키퍼 지정 가게 수는
     그 동 실제 점포 수(상가)의 5%를 반올림, 최소 1·최대 2곳 — 지정 현황은 공개 자료가 없어 가정값이다(기획안 8절).
  5. 본인 등록(D2): 대상자 절반(가정값)이 단골 질문 2개에 답했다고 둔다. 답한 사람은 그 동에서 먼저 물을 창구
     (agent.counterpart_kind)를 따른다 — 경로당·마을회관이면 그 동 실제 시설 하나, 가게면 그 집단 상대방 업종 중
     하나(결제 비중 비례)의 가게. 지정 가게가 있으면 반은 그 가게, 반은 지정 안 된 새 가상 가게를 등록한다.

재현: 시드 고정(SEED). 같은 입력이면 바이트 단위로 같은 파일이 나온다(--check로 확인).
입력: data/external/mois_single_household/*.csv (git), data/reference/dong_code.csv · app/facilities.csv (git),
      data/processed/segment_industry.parquet · dong_industry_stores.parquet · fac_dong.parquet
      (scripts/build_segment_industry.py · build_facility.py — 카드·상가 원본 필요)
실행: python scripts/build_synthetic.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from balgil.agent import (BREAK_AGES, CITY_SGG, SGG_CITY, counterpart_industries, counterpart_kind,  # noqa: E402
                          load_inputs, read_places, read_roster)
from build_external import TARGET_SGG_NM, _read_mois  # noqa: E402

OUT = ROOT / "data" / "synthetic"
ROSTER = OUT / "roster_가상.csv"
PLACES = OUT / "places_가상.csv"

SEED = 20261018                       # D4 시작일. 바꾸면 다른 명부가 나온다
N_TOTAL = 41                          # 명부 전체 (기획안 8절 표)
DEMO = ("강원 춘천시", "여성", "70대")  # 시연 칸 (기획안 9절)
DEMO_N = 8
# 장면 재현용으로 먼저 두는 사람: 칸 → [(동, 칸 안 오래된 순 자리 0부터)]. 나이는 그 동 분포에서 뽑는다
FIXED = {DEMO: [("교동", 0), ("교동", 2)],                     # 9절 "확인 권고 3명 중 2명이 교동에 삽니다(명부 주소)"
         ("강원 춘천시", "여성", "80대"): [("북산면", 1)]}       # 터전 약한 순 1위, 창구 = 경로당·마을회관(#38)
CELL_MIN, CELL_MAX = 2, 4
AGE_RANGE = {"60대": range(65, 70), "70대": range(70, 80), "80대": range(80, 90)}  # 명부 사업이 65세 이상
CONTACT_FROM, CONTACT_TO = pd.Timestamp("2025-05-01"), pd.Timestamp("2025-07-19")  # 화면 첫 기준일 07/20 전
ROSTER_KINDS = ["노인맞춤돌봄", "독거노인 안전확인", "기초연금"]  # 화면 표시용. 같은 확률
GK_RATE, GK_MIN, GK_MAX = 0.05, 1, 2  # 게이트키퍼 지정 가게: 실제 점포 수의 5%, 1~2곳 (가정값)
REGISTER_RATE = 0.5                   # 본인 등록(D2)에 답한 비율 (가정값)
NOTE_PERSON = "가상 데이터 — 실제 인물이 아닙니다"
NOTE_SHOP = "가상 가게 — 실제 상호가 아닙니다"
NOTE_FAC = "실제 공공시설 위치(전국마을회관및경로당표준데이터) — 이용자 정보는 가상"


# ------------------------------------------------------------------ 집계 분포 (실제)
def single_household() -> pd.DataFrame:
    """행정동 × 성 × 1세 나이의 1인세대수 (행안부 2025-12, 47개 동). 집계 분포만 쓰고 레코드는 없다."""
    raw = _read_mois("mois_single_household")
    raw["SGG_NM"] = raw["시군구명"].map(TARGET_SGG_NM)
    codes = pd.read_csv(ROOT / "data" / "reference" / "dong_code.csv", dtype=str, encoding="utf-8-sig")
    raw = raw.merge(codes[["SGG_NM", "ADM_CD", "ADM_NM"]], left_on=["SGG_NM", "읍면동명"],
                    right_on=["SGG_NM", "ADM_NM"], how="inner")
    assert raw["ADM_CD"].nunique() == 47, "행안부 동 이름이 dong_code.csv 47개와 다 맞지 않습니다"
    rows = []
    for band, ages in AGE_RANGE.items():
        for sex, suf in (("남성", "남자"), ("여성", "여자")):
            for a in ages:
                rows.append(raw[["SGG_NM", "ADM_CD", "ADM_NM"]].assign(성=sex, 연령대=band, 나이=a, 수=raw[f"{a}세{suf}"]))
    out = pd.concat(rows, ignore_index=True)
    return out.sort_values(["SGG_NM", "성", "연령대", "ADM_CD", "나이"], ignore_index=True)


def allocate(hh: pd.DataFrame) -> pd.Series:
    """칸 인원. 시연 칸 8명, 나머지 33명은 1인세대수 비례(최대 나머지 방식) 뒤 2~4명으로 자른다."""
    size = hh.groupby(["SGG_NM", "성", "연령대"])["수"].sum()
    rest = size.drop(DEMO)
    left = N_TOTAL - DEMO_N
    n = pd.Series(CELL_MIN, index=rest.index)
    while n.sum() < left:  # 한 명씩, 「몫 − 받은 인원」이 가장 큰 칸에 준다 (상한 4)
        want = rest / rest.sum() * left - n
        want[n >= CELL_MAX] = -np.inf
        n[want.idxmax()] += 1
    n[DEMO] = DEMO_N
    assert n.sum() == N_TOTAL and len(n) == 12
    return n.sort_index()


# ------------------------------------------------------------------ 명부
def make_roster(hh: pd.DataFrame, n_cell: pd.Series, rng: np.random.Generator) -> pd.DataFrame:
    people = []
    for (sgg, sex, band), k in n_cell.items():
        pool = hh[(hh["SGG_NM"] == sgg) & (hh["성"] == sex) & (hh["연령대"] == band) & (hh["수"] > 0)].reset_index(drop=True)
        fixed, slots = [], [slot for _, slot in FIXED.get((sgg, sex, band), [])]
        for dong, _ in FIXED.get((sgg, sex, band), []):
            q = pool[pool["ADM_NM"] == dong].reset_index(drop=True)
            fixed.append(q.iloc[rng.choice(len(q), p=q["수"] / q["수"].sum())])
        picks = [pool.iloc[i] for i in rng.choice(len(pool), k - len(fixed), p=pool["수"] / pool["수"].sum())]
        span = (CONTACT_TO - CONTACT_FROM).days
        days = sorted(rng.choice(span + 1, k, replace=False))  # 칸 안에서 접촉일이 겹치지 않게
        dates = [CONTACT_FROM + pd.Timedelta(days=int(d)) for d in days]  # 오래된 순
        if fixed:  # 먼저 둔 사람을 정해 둔 자리에, 나머지는 남은 자리에 뽑힌 순서대로
            order = slots + [i for i in range(k) if i not in slots]
            dates = [dates[i] for i in order]
        for r, d in zip(fixed + picks, dates):
            people.append({"시군구": sgg, "성": sex, "연령대": band, "나이": int(r["나이"]), "행정동코드": r["ADM_CD"],
                           "행정동": r["ADM_NM"], "마지막접촉일": d})
    p = pd.DataFrame(people)
    p["명부종류"] = rng.choice(ROSTER_KINDS, len(p))
    p = p.sort_values(["시군구", "성", "연령대", "마지막접촉일"], ascending=[False, True, True, True], ignore_index=True)
    p.insert(0, "대상자ID", [f"V{i:03d}" for i in range(1, len(p) + 1)])  # V = 가상
    return p


# ------------------------------------------------------------------ 발길이 닿던 곳
def make_places(inp) -> tuple[pd.DataFrame, dict]:
    """경로당·마을회관은 실제 시설 위치 그대로(현수 C3, F+행 번호), 가게는 게이트키퍼 지정 가게만 가상으로 만든다.
    지자체가 아는 가게는 지정 가게와 본인이 등록한 가게뿐이라, 그 밖의 가게는 표에 넣지 않는다."""
    fac = pd.read_csv(ROOT / "data" / "reference" / "app" / "facilities.csv", dtype=str, encoding="utf-8-sig")
    fac["장소ID"] = [f"F{i:03d}" for i in range(1, len(fac) + 1)]  # 원본 행 번호 — 도서관 행도 번호는 차지한다
    fac = fac[fac["세부유형"].isin(["경로당", "마을회관"])]  # 도서관은 창구 후보에서 뺀다(#27 안건 4, 10/17)
    rows = [{"장소ID": r.장소ID, "종류": r.세부유형, "이름": r.시설명, "행정동코드": r.ADM_CD, "업종": "",
             "게이트키퍼": "N", "비고": NOTE_FAC} for r in fac.itertuples()]

    industries = {city: sorted({u for s in ["남성", "여성"] for a in BREAK_AGES
                                for u in counterpart_industries(inp, city, s, a)["업종"]}) for city in CITY_SGG}
    st = inp.dong_stores
    shops = []
    for d in inp.dong.sort_values("ADM_CD").itertuples():
        for ind in industries[d.도시]:
            n_real = st[(st["SGG_NM"] == d.SGG_NM) & (st["ADM_NM"] == d.ADM_NM) & (st["업종"] == ind)]["점포수"].sum()
            n_gk = 0 if n_real == 0 else int(min(GK_MAX, max(GK_MIN, round(GK_RATE * n_real))))
            shops += [{"행정동코드": d.ADM_CD, "동": d.ADM_NM, "업종": ind, "게이트키퍼": "Y"} for _ in range(n_gk)]
    return pd.DataFrame(rows), {"industries": industries, "shops": shops}


def register(roster: pd.DataFrame, inp, gk: dict, rng: np.random.Generator) -> tuple[pd.DataFrame, list]:
    """본인 등록(D2) 결과로 등록장소ID를 채운다. 답한 사람만, 그 동의 창구를 따른다."""
    fac = pd.read_csv(ROOT / "data" / "reference" / "app" / "facilities.csv", dtype=str, encoding="utf-8-sig")
    fac["장소ID"] = [f"F{i:03d}" for i in range(1, len(fac) + 1)]
    fac = fac[fac["세부유형"].isin(["경로당", "마을회관"])]
    shops, extra, reg, kinds = gk["shops"], [], [], []
    for r in roster.itertuples():
        city = SGG_CITY[r.시군구]
        kind = counterpart_kind(inp, city, r.성, r.연령대, r.행정동코드)["창구"]
        kinds.append(kind)
        if rng.random() >= REGISTER_RATE:
            reg.append("")
            continue
        near = fac[fac["ADM_CD"] == r.행정동코드]
        if kind == "경로당·마을회관" and len(near):
            reg.append(near["장소ID"].iloc[int(rng.integers(len(near)))])
            continue
        ind = counterpart_industries(inp, city, r.성, r.연령대)
        u = rng.choice(ind["업종"].to_numpy(), p=(ind["비중"] / ind["비중"].sum()).to_numpy())
        known = [i for i, s in enumerate(shops) if s["행정동코드"] == r.행정동코드 and s["업종"] == u]
        if known and rng.random() < 0.5:
            reg.append(("GK", known[int(rng.integers(len(known)))]))
        else:
            extra.append({"행정동코드": r.행정동코드, "동": r.행정동, "업종": u, "게이트키퍼": "N"})
            reg.append(("NEW", len(extra) - 1))
    return pd.DataFrame({"등록": reg, "창구": kinds}), extra


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(SEED)
    inp = load_inputs()
    if inp.industry is None or inp.dong_stores is None or inp.facilities is None:
        raise SystemExit("data/processed/의 segment_industry · dong_industry_stores · fac_dong이 필요합니다 "
                         "(scripts/build_segment_industry.py, build_facility.py)")
    hh = single_household()
    roster = make_roster(hh, allocate(hh), rng)
    places, gk = make_places(inp)
    reg, extra = register(roster, inp, gk, rng)

    # 가게에 ID와 가상 이름을 붙인다: 지정 가게 다음에 등록으로 생긴 가게, 동·업종 순
    shops = pd.DataFrame(gk["shops"] + extra).assign(_src=["GK"] * len(gk["shops"]) + ["NEW"] * len(extra),
                                                     _i=list(range(len(gk["shops"]))) + list(range(len(extra))))
    shops = shops.sort_values(["행정동코드", "업종", "게이트키퍼", "_src", "_i"], ascending=[True, True, False, True, True],
                              ignore_index=True)
    shops["장소ID"] = [f"S{i:03d}" for i in range(1, len(shops) + 1)]
    shops["이름"] = [f"(가상) {d} {u} {k}" for d, u, k in
                     zip(shops["동"], shops["업종"], shops.groupby(["행정동코드", "업종"]).cumcount() + 1)]
    sid = {(s, i): pid for s, i, pid in zip(shops["_src"], shops["_i"], shops["장소ID"])}
    roster["등록장소ID"] = [sid[x] if isinstance(x, tuple) else x for x in reg["등록"]]
    shops = shops.assign(종류="가게", 비고=NOTE_SHOP)[["장소ID", "종류", "이름", "행정동코드", "업종", "게이트키퍼", "비고"]]
    places = pd.concat([places, shops], ignore_index=True)

    roster["마지막접촉일"] = roster["마지막접촉일"].dt.strftime("%Y-%m-%d")
    roster["비고"] = NOTE_PERSON
    roster = roster[["대상자ID", "시군구", "성", "연령대", "나이", "행정동코드", "행정동", "마지막접촉일", "명부종류",
                     "등록장소ID", "비고"]]
    return roster, places


def write(df: pd.DataFrame, path: Path) -> str:
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def report(roster: pd.DataFrame, places: pd.DataFrame) -> None:
    inp = load_inputs()
    r = read_roster(ROSTER, inp, pd.Timestamp("2025-07-20"))  # 화면 첫 기준일에서도 검사 통과
    p = read_places(PLACES, inp)
    print(f"명부 {len(r)}명 · 칸 {r.groupby(['시군구', '성', '연령대']).ngroups}개 · 동 {r['행정동코드'].nunique()}개 · "
          f"등록 {int((roster['등록장소ID'] != '').sum())}명")
    print(r.groupby(["시군구", "성", "연령대"]).size().unstack().to_string())
    print(f"장소 {len(p)}곳 {p['종류'].value_counts().to_dict()} · 지정 가게 {int(((p['종류'] == '가게') & (p['게이트키퍼'] == 'Y')).sum())}")
    demo = roster[(roster["시군구"] == DEMO[0]) & (roster["성"] == DEMO[1]) & (roster["연령대"] == DEMO[2])]
    print(f"시연 칸 {len(demo)}명 — 오래된 순 동: {' · '.join(demo['행정동'])}")


def main() -> None:
    ap = argparse.ArgumentParser(description="페르소나 가상 데이터(D4)")
    ap.add_argument("--check", action="store_true", help="두 번 만들어 바이트 단위로 같은지 확인")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    roster, places = build()
    h = (write(roster, ROSTER), write(places, PLACES))
    print(f"{ROSTER.relative_to(ROOT)} sha256 {h[0]} · {PLACES.relative_to(ROOT)} sha256 {h[1]}")
    if a.check:
        r2, p2 = build()
        same = r2.equals(roster) and p2.equals(places) and (write(r2, ROSTER), write(p2, PLACES)) == h
        print("재생성 결과:", "바이트 단위로 같음" if same else "다름!")
        assert same
    report(roster, places)


if __name__ == "__main__":
    main()
