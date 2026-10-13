"""발길 에이전트 (D1) — 뼈대.

판단은 규칙이 하고, 이 파일은 재분석 산출물을 읽어 도구 11개를 한 흐름으로 묶는다.
LLM은 부르지 않는다. 문장은 고정 틀에 계산값을 슬롯으로 넣는다(E6 5.2).

지금 되는 것 (데이터로 되는 도구)
  measure_breadth · measure_quality   양·질      ← features_segment(_month)  (A2, PR #12)
  detect_break · correct_shock        연속성      ← reanalysis break_daily    (b2_continuity, 7일 창)
  map_ground                          터전        ← features_dong             (A4, PR #12)
  rate_state                          네 상태 판정
  match_roster                        명부 교차    ← 가상 명부 (입력 형식: docs/agent_입력형식.md)
  find_counterpart                    상대방 업종·동 점포 수 ← segment_industry · dong_industry_stores
                                      (scripts/build_segment_industry.py). D4 장소 표가 오면 장소까지
  counterpart_kind                    먼저 물을 창구(가게 / 경로당·마을회관) ← 위 + fac_dong (build_facility.py)
  draft_outreach · inquiry_script     고정 문장 틀, 창구별 문의 문구
  briefing_tables                     D3 화면용 표 넷 (--out)
아직 안 되는 것 (자원 정제본·종결 형식 확정 뒤, 10/18–20)
  match_resource · log_outcome

단위 원칙 (#14, #20)
  끊김·좁아짐은 시군구 × 성 × 연령 집단이다. 카드 지표는 동에 붙이지 않는다.
  명부는 같은 칸(시군구 × 성 × 연령대)으로 거르고, 행정동은 대상자 주소에서만 가져와 터전을 붙인다.
  판정은 실행일 하루가 아니라 지난 7일 창이다(조기성: 실행일만 보면 끊김 14건 중 평균 5.7건을 놓친다).

입력은 data/processed/ 산출물을 먼저 찾고, 없으면 저장소에 커밋된 reanalysis/reference/ 를 쓴다.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

REANALYSIS_DIR = PROCESSED_DIR / "reanalysis"
REFERENCE_DIR = ROOT / "reanalysis" / "reference"

CITY_SGG = {"강남": "서울 강남구", "춘천": "강원 춘천시"}
SGG_CITY = {v: k for k, v in CITY_SGG.items()}
BREAK_AGES = ["60대", "70대", "80대"]  # 끊김 감시 대상 (b2_continuity와 같음)
COMPARE_AGE = "50대"                   # 양·질을 견주는 기준 연령 (기획안 9절 시나리오)
WINDOW_DAYS = 7
NARROW_TOP = 7                         # 90대 뺀 32칸 중 좁아짐 상위 7칸(21.9%) — 모델 라벨과 같은 선
GROUND_BOTTOM = 0.2                    # 도시 안 터전점수 하위 20%를 터전 없음 후보로 (기획안 3절 분위수 기준)
SEVERITY = {"빨강(필수까지 끊김)": 2, "주황(대면만 끊김)": 1, "-": 0}

# reanalysis/reference/features_dong.csv → 동 패널 열 이름
_REF_DONG = {"행정동코드": "ADM_CD", "이름(추정)": "ADM_NM", "60대 이상 비중": "60대이상_비중",
             "일요일÷평일": "일요일_평일비", "저녁 비중": "저녁비중", "12월÷9월": "겨울유지",
             "터전 점수(통신)": "터전점수_통신", "순위": "터전순위_통신"}
_SK_OLD_CODE = {"11230740": "11230511"}  # 개포3동 (build_dong_panel.py와 같음)


# ------------------------------------------------------------------ 입력
def _first(*paths: Path) -> Path:
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError(f"입력이 없습니다: {[str(p) for p in paths]}")


@dataclass
class Inputs:
    segment: pd.DataFrame        # 36칸 × 6개월 평균 (양·질·좁아짐 점수)
    segment_month: pd.DataFrame  # 36칸 × 월
    breaks: pd.DataFrame         # 12집단 × 일 (보정 단계별 편차와 판정)
    dong: pd.DataFrame           # 47동 (터전)
    industry: pd.DataFrame | None = None  # 집단 × 상대방 후보 업종 쏠림 (build_segment_industry.py)
    dong_stores: pd.DataFrame | None = None  # 동 × 업종 점포 수 (같은 스크립트, 상가 원본 필요)
    facilities: pd.DataFrame | None = None   # 동 × 경로당·도서관 수 (현수 build_facility.py, C3)
    sources: dict = field(default_factory=dict)


def load_inputs() -> Inputs:
    p_seg = _first(PROCESSED_DIR / "features_segment.parquet", REFERENCE_DIR / "features_segment.csv")
    p_mon = _first(PROCESSED_DIR / "features_segment_month.parquet", REFERENCE_DIR / "features_segment_month.csv")
    p_brk = _first(REANALYSIS_DIR / "break_daily.csv", REFERENCE_DIR / "break_daily.csv")
    p_dong = _first(PROCESSED_DIR / "features_dong.parquet", REFERENCE_DIR / "features_dong.csv")

    read = lambda p: pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p, encoding="utf-8-sig")
    seg, mon, brk, dong = read(p_seg), read(p_mon).rename(columns={"m": "month"}), read(p_brk), read(p_dong)

    brk["date"] = pd.to_datetime(brk["date"])
    brk["AGE"] = brk["band"]
    if "SGG_NM" not in dong:  # reference CSV
        dong = dong.rename(columns=_REF_DONG)
        dong["ADM_CD"] = dong["ADM_CD"].astype(str).replace(_SK_OLD_CODE)
        dong["ADM_NM"] = dong["ADM_NM"].str.replace(r"\(.*\)$", "", regex=True)
        dong["SGG_NM"] = dong["도시"].map(CITY_SGG)
    dong["ADM_CD"] = dong["ADM_CD"].astype(str)
    src = {"segment": p_seg, "segment_month": p_mon, "breaks": p_brk, "dong": p_dong}
    opt = {}
    for key, name in [("industry", "segment_industry.parquet"), ("dong_stores", "dong_industry_stores.parquet"),
                      ("facilities", "fac_dong.parquet")]:
        path = PROCESSED_DIR / name
        opt[key] = pd.read_parquet(path) if path.exists() else None
        if path.exists():
            src[key] = path
    return Inputs(seg, mon, brk, dong, sources=src, **opt)


def seg_name(city: str, sex: str, age: str) -> str:
    return f"{city} {sex[0]} {age}"


def _row(df: pd.DataFrame, city: str, sex: str, age: str) -> pd.Series:
    r = df[(df["city"] == city) & (df["sex"] == sex) & (df["AGE"] == age)]
    if r.empty:
        raise KeyError(f"집단 없음: {city} {sex} {age}")
    return r.iloc[0]


# ------------------------------------------------------------------ 양·질
def measure_breadth(inp: Inputs, city: str, sex: str, age: str, month: int | None = None) -> dict:
    """유효 발길 수(1/Σp²). month를 주면 그 달, 아니면 6개월 값. 같은 도시·성 50대와 견준다."""
    df = inp.segment if month is None else inp.segment_month[inp.segment_month["month"] == month]
    v, ref = _row(df, city, sex, age)["breadth"], _row(df, city, sex, COMPARE_AGE)["breadth"]
    return {"값": float(v), "50대": float(ref), "50대 대비": float(v / ref)}


def measure_quality(inp: Inputs, city: str, sex: str, age: str, month: int | None = None) -> dict:
    """체류 비중(%, 거주자 결제 건수 기준, 분모는 전 업종). 같은 도시·성 50대와 견준다."""
    df = inp.segment if month is None else inp.segment_month[inp.segment_month["month"] == month]
    v, ref = _row(df, city, sex, age)["stay"], _row(df, city, sex, COMPARE_AGE)["stay"]
    return {"값": float(v), "50대": float(ref), "50대 대비": float(v / ref)}


def narrow_cells(inp: Inputs) -> pd.DataFrame:
    """좁아짐 집단: 나이·도시 효과를 덜어 낸 좁아짐 점수(narrow)로 90대 뺀 32칸 중 상위 7칸."""
    s = inp.segment[inp.segment["AGE"] != "90대"].copy()
    s["좁아짐순위"] = s["narrow"].rank(ascending=False).astype(int)
    return s[s["좁아짐순위"] <= NARROW_TOP].sort_values("좁아짐순위")


# ------------------------------------------------------------------ 연속성
def _window(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> pd.DataFrame:
    b = inp.breaks
    w = b[(b["city"] == city) & (b["sex"] == sex) & (b["band"] == age)
          & b["date"].between(as_of - pd.Timedelta(days=WINDOW_DAYS - 1), as_of)]
    return w.sort_values("date")


def detect_break(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> dict:
    """지난 7일 창에서 보정 후(z2) 끊김이 있었는가. 빨강 = 필수까지 끊김, 주황 = 대면만 끊김."""
    w = _window(inp, city, sex, age, as_of)
    hit = w[w["state"] != "-"]
    worst = max(hit["state"], key=SEVERITY.get) if len(hit) else "-"
    pct = lambda d: int(round((np.exp(d.min()) - 1) * 100)) if len(d) else 0
    return {"상태": worst, "끊김 일수": len(hit), "창 일수": len(w),
            "끊긴 날": [d.strftime("%m/%d") for d in hit["date"]], "공휴일 주간": bool(w["holwk"].any()),
            "대면 최저(%)": pct(w["f_d2"]), "필수 최저(%)": pct(w["e_d2"])}


def correct_shock(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> dict:
    """보정 단계별로 창 안의 경보 일수. (0) 보정 없음 → (1) 계절형 → (2) + 같은 도시 30·40대 차감."""
    w = _window(inp, city, sex, age, as_of)
    return {"보정 없음": int(w["al0"].sum()), "계절형 보정": int(w["al1"].sum()), "공통 충격 보정": int(w["al2"].sum())}


# ------------------------------------------------------------------ 터전
def map_ground(inp: Inputs, adm_cd: str) -> dict:
    """동의 터전(통신). 터전점수는 도시 안 순위 평균이고 낮을수록 약하다. 공급 지표로 쓴다(#6)."""
    d = inp.dong[inp.dong["ADM_CD"] == str(adm_cd)]
    if d.empty:
        raise KeyError(f"동 패널에 없는 행정동코드: {adm_cd}")
    r = d.iloc[0]
    n = int((inp.dong["도시"] == r["도시"]).sum())
    return {"동": r["ADM_NM"], "도시": r["도시"], "터전점수": float(r["터전점수_통신"]), "순위": int(r["터전순위_통신"]),
            "동 수": n, "하위 20%": int(r["터전순위_통신"]) <= int(np.ceil(n * GROUND_BOTTOM)),
            "저녁비중": float(r["저녁비중"]), "일요일_평일비": float(r["일요일_평일비"])}


def ground_alerts(inp: Inputs) -> pd.DataFrame:
    """도시마다 터전점수 하위 20% 동 — 사람이 아니라 동 단위 정책으로 나간다."""
    out = []
    for city, g in inp.dong.groupby("도시"):
        k = int(np.ceil(len(g) * GROUND_BOTTOM))
        out.append(g.nsmallest(k, "터전점수_통신"))
    return pd.concat(out)[["도시", "ADM_CD", "ADM_NM", "터전점수_통신", "터전순위_통신"]]


# ------------------------------------------------------------------ 판정
@dataclass
class State:
    집단: str
    상태: str          # 끊김(빨강) / 끊김(주황) / 좁아짐 / 정상
    근거: dict


def rate_state(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> State:
    """네 상태 중 집단 단위 셋을 판정한다. 터전 없음은 동 단위라 ground_alerts가 따로 낸다(기획안 3절)."""
    month = as_of.month
    ev = {"양": measure_breadth(inp, city, sex, age, month), "질": measure_quality(inp, city, sex, age, month)}
    narrow = narrow_cells(inp)
    ev["좁아짐 상위"] = bool(((narrow["city"] == city) & (narrow["sex"] == sex) & (narrow["AGE"] == age)).any())
    if age in BREAK_AGES:
        ev["연속성"] = detect_break(inp, city, sex, age, as_of)
        ev["보정"] = correct_shock(inp, city, sex, age, as_of)
        if ev["연속성"]["상태"] != "-":
            color = "빨강" if ev["연속성"]["상태"].startswith("빨강") else "주황"
            return State(seg_name(city, sex, age), f"끊김({color})", ev)
    return State(seg_name(city, sex, age), "좁아짐" if ev["좁아짐 상위"] else "정상", ev)


# ------------------------------------------------------------------ 명부·상대방·자원
ROSTER_COLUMNS = ["대상자ID", "시군구", "성", "연령대", "행정동코드", "마지막접촉일", "명부종류"]


ROSTER_VALUES = {"시군구": set(CITY_SGG.values()), "성": {"남성", "여성"}, "연령대": set(BREAK_AGES)}
PLACE_COLUMNS = ["장소ID", "종류", "이름", "행정동코드", "업종", "게이트키퍼"]
PLACE_KINDS = {"가게", "경로당", "마을회관"}


def _bad_rows(df: pd.DataFrame, mask: pd.Series, id_col: str, what: str) -> str:
    rows = df.loc[mask]
    fmt = lambda v: v.strftime("%Y-%m-%d") if isinstance(v, pd.Timestamp) else v
    shown = ", ".join(f"{i}({fmt(v)})" for i, v in zip(rows[id_col].head(5), rows[what].head(5)))
    return f"{what} 값이 허용 범위 밖인 행 {int(mask.sum())}개: {shown}"


def _check_dong(df: pd.DataFrame, inp: Inputs, id_col: str) -> pd.DataFrame:
    """행정동코드는 SGIS 8자리(dong_code.csv의 ADM_CD 47개)만 받는다. 예전 SK 코드는 바꿔 주고, 그 밖은 멈춘다."""
    df["행정동코드"] = df["행정동코드"].astype(str).str.strip().replace(_SK_OLD_CODE)
    bad = ~df["행정동코드"].isin(set(inp.dong["ADM_CD"]))
    if bad.any():
        raise ValueError(_bad_rows(df, bad, id_col, "행정동코드")
                         + " — SGIS 8자리(data/reference/dong_code.csv의 ADM_CD)만 됩니다. 행안부 10자리는 안 됩니다"
                         " (예전 SK 코드 11230740만 개포3동으로 바꿔 받습니다)")
    return df


def read_roster(path: Path, inp: Inputs, as_of: pd.Timestamp) -> pd.DataFrame:
    """명부를 읽고 검사한다. 값이 틀린 행이 조용히 교차에서 빠지지 않도록 멈춘다(현수 #27 리뷰).
    90대는 끊김을 판정하지 않아 일부러 빼는 것이므로 경고만 낸다."""
    r = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    missing = [c for c in ROSTER_COLUMNS if c not in r]
    if missing:
        raise ValueError(f"명부에 필수 열이 없습니다: {missing} (docs/agent_입력형식.md)")
    for c in ROSTER_COLUMNS:
        r[c] = r[c].str.strip()
    if r["대상자ID"].duplicated().any():
        raise ValueError(f"대상자ID가 겹칩니다: {sorted(set(r.loc[r['대상자ID'].duplicated(), '대상자ID']))[:5]}")
    old = r["연령대"] == "90대"
    if old.any():
        print(f"[경고] 90대 {int(old.sum())}명은 끊김 판정 대상이 아니라 교차에서 뺍니다")
        r = r[~old].copy()
    for c, ok in ROSTER_VALUES.items():
        bad = ~r[c].isin(ok)
        if bad.any():
            raise ValueError(_bad_rows(r, bad, "대상자ID", c) + f" — 허용값 {sorted(ok)}")
    r = _check_dong(r, inp, "대상자ID")
    r["마지막접촉일"] = pd.to_datetime(r["마지막접촉일"], errors="coerce")
    if r["마지막접촉일"].isna().any():
        raise ValueError(_bad_rows(r, r["마지막접촉일"].isna(), "대상자ID", "대상자ID") + " — 마지막접촉일은 YYYY-MM-DD")
    late = r["마지막접촉일"] > as_of
    if late.any():
        raise ValueError(_bad_rows(r, late, "대상자ID", "마지막접촉일")
                         + f" — 기준일 {as_of:%Y-%m-%d}보다 늦습니다. 접촉일은 가장 이른 시연 기준일 이전으로 만듭니다")
    return r


def read_places(path: Path, inp: Inputs) -> pd.DataFrame:
    """발길이 닿던 곳 표(D4)를 읽고 검사한다. 행정동코드를 문자열로 고정한다 — 정수로 읽히면 비교가 0건이 된다."""
    p = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    missing = [c for c in PLACE_COLUMNS if c not in p]
    if missing:
        raise ValueError(f"장소 표에 필수 열이 없습니다: {missing} (docs/agent_입력형식.md 2절)")
    for c in PLACE_COLUMNS:
        p[c] = p[c].fillna("").str.strip()
    for c, ok in {"종류": PLACE_KINDS, "게이트키퍼": {"Y", "N"}}.items():
        bad = ~p[c].isin(ok)
        if bad.any():
            raise ValueError(_bad_rows(p, bad, "장소ID", c) + f" — 허용값 {sorted(ok)}")
    shop_no_ind = (p["종류"] == "가게") & (p["업종"] == "")
    if shop_no_ind.any():
        raise ValueError(_bad_rows(p, shop_no_ind, "장소ID", "업종") + " — 가게는 카드 업종 이름이 필요합니다")
    return _check_dong(p, inp, "장소ID")


def match_roster(roster: pd.DataFrame, city: str, sex: str, age: str, as_of: pd.Timestamp, top_n: int = 3) -> pd.DataFrame:
    """끊긴 칸(시군구 × 성 × 연령대)으로 명부를 거르고, 마지막 접촉이 오래된 순으로 top_n명.
    행정동은 거르는 데 쓰지 않는다 — 결과에 붙여 터전과 상대방 후보를 찾는 데만 쓴다."""
    m = roster[(roster["시군구"] == CITY_SGG[city]) & (roster["성"] == sex) & (roster["연령대"] == age)].copy()
    m["경과일"] = (as_of - m["마지막접촉일"]).dt.days
    return m.sort_values("경과일", ascending=False).head(top_n).assign(칸_인원=len(m))


COUNTERPART_SHARE_MIN = 0.03  # 후보 업종 결제의 3% 미만인 업종은 쏠림이 커도 "평소 가던 곳"이라 보기 어렵다


def counterpart_industries(inp: Inputs, city: str, sex: str, age: str, n: int = 3) -> pd.DataFrame | None:
    """그 집단의 평소 발길이 닿던 업종 n개 (기획안 4절 2단계 ①).
    비중 상위 n-1개에, 같은 도시 전 연령보다 더 몰린(쏠림 최대) 업종 하나를 더한다.
    비중만 보면 어느 집단이나 한식·약국이라, 쏠림이 그 집단다운 곳(예: 춘천 여성 고령의 미용실)을 살린다."""
    if inp.industry is None:
        return None
    g = inp.industry[(inp.industry["city"] == city) & (inp.industry["sex"] == sex) & (inp.industry["AGE"] == age)]
    g = g[g["비중"] >= COUNTERPART_SHARE_MIN]
    top = g.nlargest(n - 1, "비중")
    rest = g.drop(top.index)
    return pd.concat([top, rest.nlargest(1, "쏠림")])[["업종", "발길분류", "비중", "쏠림"]]


def find_counterpart(inp: Inputs, city: str, sex: str, age: str, adm_cd: str | None = None,
                     places: pd.DataFrame | None = None, n: int = 3) -> pd.DataFrame | None:
    """발길이 닿던 곳 후보 (기획안 4절 2단계).
    ① 집단의 평소 업종 쏠림 → ② 대상자 동의 그 업종 점포 수(상가) → ③ D4 장소 표가 있으면 그 동의 해당 업종
    가게와 경로당·마을회관을 게이트키퍼 지정 순으로 (#6: 가게가 적은 동은 경로당·마을회관이 창구). 상호는 상가에서 내지 않는다."""
    ind = counterpart_industries(inp, city, sex, age, n)
    if ind is None:
        return None
    if adm_cd is not None and inp.dong_stores is not None:
        d = inp.dong[inp.dong["ADM_CD"] == str(adm_cd)].iloc[0]
        st = inp.dong_stores[(inp.dong_stores["SGG_NM"] == d["SGG_NM"]) & (inp.dong_stores["ADM_NM"] == d["ADM_NM"])]
        ind = ind.merge(st[["업종", "점포수"]], on="업종", how="left").fillna({"점포수": 0})
    if places is not None and adm_cd is not None:
        p = places[places["행정동코드"] == str(adm_cd)]
        p = p[p["종류"].isin(["경로당", "마을회관"]) | p["업종"].isin(ind["업종"])]
        return p.sort_values(["게이트키퍼", "종류"], ascending=[False, True])
    return ind


SHOP_PER_CENTER = 3  # 상대방 업종 가게가 경로당의 3배가 안 되는 동은 경로당을 먼저 (10/17 확정 전 초안)


def counterpart_kind(inp: Inputs, city: str, sex: str, age: str, adm_cd: str) -> dict:
    """그 대상자에게 먼저 물을 창구: 가게인가 경로당·마을회관인가 (#6, #26).
    춘천 면 지역은 가게가 적고 60세+ 천 명당 경로당이 많다(60세+ 천 명당 체류형 점포 × 경로당·마을회관, 춘천 −0.79, n=25;
    강남 0.03. 분석결과 4.7, C3 #30. 수치는 10/17 수치표). 단골 가게를 전제하면 터전점수가 낮아
    확인 창구가 가장 필요한 동에서 2단계가 빈다. 그 동의 상대방 업종 가게 수와 경로당·마을회관 수를 견줘 고른다.
    가게 수나 경로당 수를 모르면 가게로 둔다(기획안 4절 기본값).
    데이터가 주는 것은 후보 위치까지다. 실제로 다니던 곳·연락 경로는 본인 등록(D2)으로만 받는다(07_에이전트 7.5)."""
    ind = find_counterpart(inp, city, sex, age, adm_cd)
    shops = int(ind["점포수"].sum()) if ind is not None and "점포수" in ind else None
    centers = None
    if inp.facilities is not None:
        f = inp.facilities[inp.facilities["ADM_CD"].astype(str) == str(adm_cd)]
        centers = int(f["경로당수"].iloc[0]) if len(f) else None
    first = "경로당·마을회관" if shops is not None and centers and shops < SHOP_PER_CENTER * centers else "가게"
    return {"창구": first, "가게후보": shops, "경로당": centers, "업종": ind}


# 문의 문구: 개인정보·"고립 의심" 같은 말 없이 안부 확인으로 연다(기획안 9절). 기관명만 슬롯
INQUIRY = {
    "가게": "안녕하세요, {기관}입니다. 겨울철 안부 확인 중인데요, 평소 자주 오시던 어르신 중에 요즘 통 안 보이시는 분이 계실까요?",
    "경로당·마을회관": "안녕하세요, {기관}입니다. 겨울철 안부 확인 중인데요, 경로당(마을회관)에 자주 나오시던 어르신 중에 요즘 안 나오시는 분이 계실까요?",
}


def inquiry_script(kind: str, agency: str = "OO동 행정복지센터") -> str:
    return INQUIRY[kind].format(기관=agency)


def match_resource(*_, **__):
    """상태별 자원 후보: 복지로·1365 정제본(res_*.parquet)을 거리·반복성·대면성으로 정렬(기획안 6절)."""
    raise NotImplementedError("자원 정제본(scripts/fetch_welfare_api.py 산출)을 받아 10/18–20에 붙입니다")


def log_outcome(*_, **__):
    """종결 기록(개인·집단)과 임계값 되먹임. 기록 형식은 docs/agent_입력형식.md 「종결 기록」."""
    raise NotImplementedError("종결 기록 형식 확정(10/17) 뒤에 붙입니다")


# ------------------------------------------------------------------ 문장 틀
def _counterpart_text(cp: pd.DataFrame | None) -> str:
    if cp is None or cp.empty:
        return "업종 쏠림 표 없음 (scripts/build_segment_industry.py)"
    has_n = "점포수" in cp
    return " · ".join(f"{r.업종}" + (f" {int(r.점포수)}곳" if has_n else f" {r.비중:.0%}") for r in cp.itertuples())


def _window_text(k: dict) -> str:
    shops = _counterpart_text(k["업종"])
    centers = f"경로당·마을회관 {k['경로당']}곳" if k["경로당"] is not None else "경로당 수 없음 (scripts/build_facility.py)"
    return f"경로당·마을회관 먼저 — {centers} (가게: {shops})" if k["창구"] == "경로당·마을회관" else f"가게 먼저 — {shops} ({centers})"


def draft_outreach(st: State, people: pd.DataFrame | None = None) -> str:
    """고정 문장 틀 + 수치 슬롯. 명부의 이름·연락처·주소는 문장에 넣지 않는다(E6 4절)."""
    e = st.근거
    q, b = e["질"], e["양"]
    lines = [f"**{st.상태} · {st.집단}**",
             f"〈양〉 유효 발길 수 {b['값']:.1f} — 같은 도시·성 50대({b['50대']:.1f})의 {b['50대 대비']:.0%}.",
             f"〈질〉 체류 비중 {q['값']:.1f}% — 50대({q['50대']:.1f}%)의 {q['50대 대비']:.0%}."]
    if "연속성" in e:
        c, s = e["연속성"], e["보정"]
        if c["상태"] != "-":
            kind = "필수 발길(장보기·병원·약국)까지" if c["상태"].startswith("빨강") else "대면 발길만"
            lines.append(f"〈연속성〉 지난 {WINDOW_DAYS}일 중 {c['끊김 일수']}일({', '.join(c['끊긴 날'])}) {kind} 평소 흔들림의 3배 밖으로 "
                         f"줄었습니다(대면 최저 {c['대면 최저(%)']:+d}%, 필수 최저 {c['필수 최저(%)']:+d}%).")
            lines.append(f"〈보정〉 같은 7일에 보정 없이 {s['보정 없음']}일 → 계절 보정 {s['계절형 보정']}일 → "
                         f"같은 도시 30·40대 차감 {s['공통 충격 보정']}일.")
            if e.get("동시 끊김"):
                k, n = e["동시 끊김"]
                lines.append(f"〈동시〉 같은 도시 고령 {n}개 집단 중 {k}개가 같은 7일에 함께 끊겼습니다"
                             + (" (공휴일 주간과 겹침)" if c["공휴일 주간"] else "")
                             + ". 30·40대를 빼고도 남은 공통 사건일 수 있습니다.")
        else:
            lines.append(f"〈연속성〉 지난 {WINDOW_DAYS}일 끊김 없음.")
    if st.상태.startswith("끊김") and "상대방" in e:
        lines.append(f"〈상대방〉 이 집단의 평소 발길이 닿던 업종: {_counterpart_text(e['상대방'])}")
    if people is not None and len(people):
        days = " · ".join(f"{d}일" for d in people["경과일"])
        lines.append(f"〈명부〉 이 칸에 드는 대상자 {int(people['칸_인원'].iloc[0])}명 중 마지막 접촉이 가장 오래된 {len(people)}명 ({days}).")
        lines += [f"  - {r.대상자ID}: 접촉 {r.경과일}일 전 · 〈터전〉 {r.터전} · 〈물어볼 곳〉 {r.물어볼곳}" for r in people.itertuples()]
        if st.상태.startswith("끊김"):
            lines += [f"〈문의 문구 · {k}〉 \"{inquiry_script(k)}\"" for k in dict.fromkeys(people["창구"])]
    if st.상태.startswith("끊김") and e.get("동시 끊김"):
        lines.append("▸ 권고: 개별 전화 전에 공통 사건(명절·한파·지역 행사)인지 먼저 확인합니다. 사건이 아니면 1단계 전화부터.")
    elif st.상태.startswith("끊김"):
        lines.append("▸ 권고: 1단계 전화. 닿지 않으면 본인이 등록한 발길이 닿던 곳(단골 가게·경로당·마을회관)에 문의"
                     + (" → 방문 전 복지서비스 후보를 붙입니다." if "빨강" in st.상태 else "."))
    elif st.상태 == "좁아짐":
        lines.append("▸ 권고: 사람이 아니라 동 단위 자원(프로그램·봉사 일감)으로 냅니다.")
    return "\n".join(lines)


# ------------------------------------------------------------------ 주간 루프
SIGNAL = {"끊김(빨강)": "빨강", "끊김(주황)": "주황", "좁아짐": "노랑", "정상": "초록"}
BREAK_KIND = {"끊김(빨강)": "필수형", "끊김(주황)": "대면형"}


@dataclass
class Week:
    as_of: pd.Timestamp
    states: list            # 12집단 State
    people: dict            # 집단 이름 → 명부 교차 결과 (끊긴 칸만)


def run_week(inp: Inputs, as_of: pd.Timestamp, roster: pd.DataFrame | None = None, top_n: int = 3) -> Week:
    """끊김 루프(주 1회) 한 번: 60·70·80대 12집단 판정 → 동시 끊김 표시 → 끊긴 칸만 상대방 업종·명부 교차."""
    states = [rate_state(inp, c, s, a, as_of) for c in CITY_SGG for s in ["남성", "여성"] for a in BREAK_AGES]
    broken = [st for st in states if st.상태.startswith("끊김")]
    # 같은 도시 고령 6집단 중 절반 이상이 같은 창에서 끊기면 개인 사건보다 공통 사건을 먼저 의심한다(기획안 2절)
    for city in CITY_SGG:
        same = [st for st in broken if st.집단.startswith(city)]
        if len(same) >= len(BREAK_AGES):
            for st in same:
                st.근거["동시 끊김"] = (len(same), 2 * len(BREAK_AGES))
    people = {}
    for st in broken:
        city, sx, age = st.집단.split()
        sex = {"남": "남성", "여": "여성"}[sx]
        st.근거["상대방"] = counterpart_industries(inp, city, sex, age)
        if roster is None:
            continue
        pp = match_roster(roster, city, sex, age, as_of, top_n)
        grounds = [map_ground(inp, cd) for cd in pp["행정동코드"]]
        pp["행정동"] = [g["동"] for g in grounds]
        pp["터전순위"] = [g["순위"] for g in grounds]
        pp["터전"] = [f"{g['동']} 터전 약한 순 {g['순위']}/{g['동 수']}" + (" (하위 20%)" if g["하위 20%"] else "") for g in grounds]
        kinds = [counterpart_kind(inp, city, sex, age, cd) for cd in pp["행정동코드"]]
        pp["창구"] = [k["창구"] for k in kinds]
        pp["물어볼곳"] = [_window_text(k) for k in kinds]
        people[st.집단] = pp
    return Week(as_of, states, people)


def weekly_briefing(inp: Inputs, as_of: pd.Timestamp, roster: pd.DataFrame | None = None, top_n: int = 3) -> str:
    """끊김 루프 한 번을 담당자용 글로 낸다. 같은 내용의 표는 briefing_tables."""
    wk = run_week(inp, as_of, roster, top_n)
    broken = sorted([st for st in wk.states if st.상태.startswith("끊김")], key=lambda st: st.상태 != "끊김(빨강)")
    blocks = [draft_outreach(st, wk.people.get(st.집단)) for st in broken]
    narrow, ground = narrow_cells(inp), ground_alerts(inp)
    n_people = sum(len(p) for p in wk.people.values())
    head = [f"# 주간 브리핑 — {as_of:%Y-%m-%d} 기준 (지난 {WINDOW_DAYS}일 창)",
            f"끊김 {len(broken)}개 집단 (빨강 {sum(st.상태 == '끊김(빨강)' for st in broken)} · 주황 {sum(st.상태 == '끊김(주황)' for st in broken)})"
            + (f", 확인 권고 {n_people}명" if roster is not None else ", 명부 없음 — 교차 생략"),
            f"좁아짐 {len(narrow)}개 집단·터전 없음 후보 {len(ground)}개 동은 사람이 아니라 동 단위로 나갑니다.", ""]
    tail = ["", "## 좁아짐 (90대 뺀 32칸 중 상위 7칸)"]
    tail += [f"- {r.seg} (점수 {r.narrow:+.2f}, {r.좁아짐순위}위)" + (" — 청년: 끊김 감시 대상 아님" if r.AGE in ("10대", "20대") else "")
             for r in narrow.itertuples()]
    tail += ["", f"## 터전 없음 후보 (도시 안 터전점수 하위 {GROUND_BOTTOM:.0%}, 공급 지표)"]
    tail += [f"- {r.도시} {r.ADM_NM} (약한 순 {r.터전순위_통신}위)" for r in ground.itertuples()]
    return "\n".join(head + ["\n\n".join(blocks) if blocks else "이번 주 끊김 없음."] + tail)


def briefing_tables(inp: Inputs, as_of: pd.Timestamp, roster: pd.DataFrame | None = None, top_n: int = 3) -> dict[str, pd.DataFrame]:
    """D3 화면이 읽는 표 넷. ① 주간 브리핑 = 요약·집단·대상자, ③ 지도 = 터전.
    카드 지표는 집단 표에만 있고 동 표에는 없다(실행계획 2절)."""
    wk = run_week(inp, as_of, roster, top_n)
    prev = run_week(inp, as_of - pd.Timedelta(days=WINDOW_DAYS))
    rows = []
    for st in wk.states:
        e, (city, sx, age) = st.근거, st.집단.split()
        c, s = e.get("연속성", {}), e.get("보정", {})
        rows.append({
            "기준일": as_of.date(), "집단": st.집단, "도시": city, "성": {"남": "남성", "여": "여성"}[sx], "연령": age,
            "신호": SIGNAL[st.상태], "상태": st.상태, "끊김종류": BREAK_KIND.get(st.상태, ""),
            "동시끊김": bool(e.get("동시 끊김")), "끊김일수": c.get("끊김 일수", 0), "끊긴날": " ".join(c.get("끊긴 날", [])),
            "대면_7일최저_pct": c.get("대면 최저(%)"), "필수_7일최저_pct": c.get("필수 최저(%)"),
            "경보_보정없음": s.get("보정 없음"), "경보_계절보정": s.get("계절형 보정"), "경보_공통충격보정": s.get("공통 충격 보정"),
            "양_유효발길수": round(e["양"]["값"], 2), "양_50대": round(e["양"]["50대"], 2),
            "질_체류비중_pct": round(e["질"]["값"], 2), "질_50대_pct": round(e["질"]["50대"], 2),
            "좁아짐상위": e["좁아짐 상위"], "상대방업종": _counterpart_text(e.get("상대방")) if st.상태.startswith("끊김") else "",
            "명부_칸인원": int(wk.people[st.집단]["칸_인원"].iloc[0]) if st.집단 in wk.people and len(wk.people[st.집단]) else None,
        })
    groups = pd.DataFrame(rows).astype({"명부_칸인원": "Int64"})
    sig = groups["신호"].value_counts()
    alarms = groups[["경보_보정없음", "경보_계절보정", "경보_공통충격보정"]].sum()
    summary = pd.DataFrame([{
        "기준일": as_of.date(), "창_일수": WINDOW_DAYS,
        "확인권고_집단": int(groups["상태"].str.startswith("끊김").sum()),
        "지난주_확인권고_집단": sum(st.상태.startswith("끊김") for st in prev.states),
        "빨강": int(sig.get("빨강", 0)), "주황": int(sig.get("주황", 0)), "노랑": int(sig.get("노랑", 0)), "초록": int(sig.get("초록", 0)),
        "확인권고_인원": sum(len(p) for p in wk.people.values()) if roster is not None else None,
        # 12집단 × 7일 중 경보일 합. 보정이 경보를 지우기도 하고(명절) 드러내기도 한다(30·40대만 오른 주)
        "경보일_보정없음": int(alarms["경보_보정없음"]), "경보일_계절보정": int(alarms["경보_계절보정"]),
        "경보일_공통충격보정": int(alarms["경보_공통충격보정"]),
    }])
    people = (pd.concat([p.assign(집단=k) for k, p in wk.people.items()], ignore_index=True)
              [["집단", "대상자ID", "명부종류", "경과일", "행정동코드", "행정동", "터전순위", "창구", "물어볼곳"]]
              if wk.people else pd.DataFrame(columns=["집단", "대상자ID", "명부종류", "경과일", "행정동코드", "행정동", "터전순위", "창구", "물어볼곳"]))
    people = people.astype({"경과일": "Int64", "터전순위": "Int64"})
    ground = inp.dong[["도시", "ADM_CD", "ADM_NM", "터전점수_통신", "터전순위_통신"]].copy()
    ground["터전없음후보"] = ground["ADM_CD"].isin(ground_alerts(inp)["ADM_CD"])
    return {"agent_summary": summary, "agent_groups": groups, "agent_people": people, "agent_ground": ground}


def main() -> None:
    ap = argparse.ArgumentParser(description="발길 에이전트 주간 브리핑 (D1 뼈대)")
    ap.add_argument("--as-of", default=None, help="기준일 YYYY-MM-DD (기본: 끊김 자료의 마지막 날)")
    ap.add_argument("--roster", type=Path, default=None, help="가상 명부 CSV (docs/agent_입력형식.md)")
    ap.add_argument("--places", type=Path, default=None, help="발길이 닿던 곳 CSV (D4). 지금은 형식 검사만, 브리핑 연결은 10/18–20")
    ap.add_argument("--top", type=int, default=3, help="끊긴 칸마다 올릴 대상자 수 (기획안 4절 상위 N명)")
    ap.add_argument("--out", type=Path, default=None, help="D3 화면용 표를 쓸 폴더 (예: data/processed/agent)")
    a = ap.parse_args()
    inp = load_inputs()
    as_of = pd.Timestamp(a.as_of) if a.as_of else inp.breaks["date"].max()
    roster = read_roster(a.roster, inp, as_of) if a.roster else None
    if a.places:
        places = read_places(a.places, inp)
        print(f"장소 표 검사 통과: {len(places)}곳 ({places['종류'].value_counts().to_dict()})\n")
    print(weekly_briefing(inp, as_of, roster, a.top))
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        for name, df in briefing_tables(inp, as_of, roster, a.top).items():
            df.to_csv(a.out / f"{name}.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
        print(f"\n표 저장: {a.out} (agent_summary · agent_groups · agent_people · agent_ground)")
    print("\n입력: " + ", ".join(f"{k}={Path(v).relative_to(ROOT)}" for k, v in inp.sources.items()))


if __name__ == "__main__":
    main()
