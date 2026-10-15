"""발길 — 담당자 화면 4개 (D3, 시연용).

실행: streamlit run app/balgil_app.py      (?screen=1~4 를 붙이면 그 화면만 — 캡처·데모용)
의존: app/requirements-app.txt (분석 쪽 requirements.txt에 화면 라이브러리를 더한 것)

읽는 파일은 모두 git에 있다 — 원본 데이터가 없어도 뜬다.
  reanalysis/reference/   재분석 결과 (끊김·보정·주간 패널)
  data/reference/app/     scripts/build_app_data.py가 만든 지도·시설·SHAP, 화면 ①의 agent.py 표(대상자 표는 가상 명부)

원칙
  * 집단 지표(양·질·연속성)는 시군구 × 성 × 연령까지만. 동 단위로 보여 주는 것은 터전뿐이다.
  * 화면 ①은 D1 agent.py 판정(빨강·주황·노랑·초록 넷)을 그대로 보인다. 기획안 3절 5단계의 초록·연두 구분과
    장보기형·병원약국형 구분은 agent.py에 규칙이 생기면 따라 바꾼다(#4 수경 코멘트).
  * 숫자는 10/17 수치 동결 뒤 docs/최종수치표.md 값으로 교체한다.

겉모양은 app/style.py(Stripe DESIGN.md 토큰). 데이터 색은 dataviz 기준 팔레트(검증: validate_palette.js)
  신호(빨강·주황·노랑)  status critical/serious/warning — 색만으로 말하지 않고 항상 점·글자를 같이 단다
  터전 지도         순차 파랑 한 가지 (진할수록 값이 큼)
  지도 위 시설 점   주황(경로당)·청록(도서관) — 범주 2·3번, 전 쌍 CVD ΔE 9.2 통과
  SHAP 막대         발산 파랑(확률을 낮춤)·빨강(높임)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import altair as alt
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as ui  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reanalysis" / "reference"
APP = ROOT / "data" / "reference" / "app"

# ── 데이터 색 (dataviz reference palette) ──────────────────────────────
SERIOUS, CRITICAL, WARNING, CALM = "#ec835a", "#d03b3b", "#fab219", "#c3ccd7"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"]  # 순차 100·250·400·500·650
POS, NEG = "#e34948", "#2a78d6"  # 발산: 확률을 높임 / 낮춤
SERIES = ["#2a78d6", "#eb6834"]  # 범주 1·2번 (선 두 개)
FAC_COLOR = {"경로당": "#eb6834", "도서관": "#1baf7a"}
SHADE = "#eef2f7"  # 공통 사건 주간 배경 띠


FEATURE_KO = {
    "m3": "좁아짐 3주 평균", "narrow": "이번 주 좁아짐", "d_narrow": "좁아짐 변화",
    "breadth_z": "발길 수 (양)", "d_breadth_z": "발길 수 변화",
    "stay_z": "체류 비중 (질)", "d_stay_z": "체류 비중 변화",
    "meal": "식사 비중", "anon": "익명 비중", "med": "병원·약국 비중", "evening": "저녁 결제 비중",
}
WEEK0 = pd.Timestamp("2025-07-07")  # weekly_panel의 w=0 주의 월요일

st.set_page_config(page_title="발길 — 담당자 화면", page_icon="👣", layout="wide")
st.html(ui.CSS)  # <style>만 있으면 앱 전체에 적용된다


@alt.theme.register("balgil", enable=True)
def chart_theme():
    return {
        "config": {
            "background": ui.CANVAS,
            "font": ui.FONT,
            "padding": {"top": 8, "left": 4, "right": 8, "bottom": 4},
            "view": {"stroke": None},
            "axis": {"labelColor": ui.MUTE, "titleColor": ui.MUTE, "gridColor": ui.HAIRLINE, "domain": False,
                     "tickColor": ui.HAIRLINE, "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 400,
                     "labelPadding": 6},
            "legend": {"labelColor": ui.INK_2, "labelFontSize": 12, "symbolSize": 80, "titleFontSize": 11},
            "title": {"color": ui.INK, "fontSize": 14, "fontWeight": 600, "anchor": "start", "offset": 12,
                      "subtitleColor": ui.MUTE, "subtitleFontSize": 12, "subtitleFontWeight": 400},
        }
    }


def card(key: str):
    return st.container(border=True, key=f"card_{key}")


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


# ── 데이터 ─────────────────────────────────────────────────────────────
@st.cache_data
def load_breaks(nomed: bool) -> pd.DataFrame:
    b = pd.read_csv(REF / ("nomed_break_daily.csv" if nomed else "break_daily.csv"), parse_dates=["date"])
    b["face_pct"] = (np.exp(b["f_d2"]) - 1) * 100
    b["ess_pct"] = (np.exp(b["e_d2"]) - 1) * 100
    b["week"] = b["date"] - pd.to_timedelta(b["date"].dt.weekday, unit="D")
    return b


@st.cache_data
def load_agent() -> tuple[pd.DataFrame, pd.DataFrame]:
    summ = pd.read_csv(APP / "agent_summary.csv", parse_dates=["기준일"])
    groups = pd.read_csv(APP / "agent_groups.csv", parse_dates=["기준일"])
    groups["상대방업종"] = groups["상대방업종"].fillna("")
    if "궂은날" in groups:  # agent.py 날씨 꼬리표(#31 수경). 표를 그 뒤에 다시 만들어야 열이 생긴다
        groups["궂은날"] = groups["궂은날"].fillna("")
    for c in ("다음행동", "자원후보"):  # agent.py next_step·match_resource(#44 수경). 표를 그 뒤에 다시 만들어야 열이 생긴다
        if c in groups:
            groups[c] = groups[c].fillna("")
    return summ, groups


@st.cache_data
def load_people() -> pd.DataFrame | None:
    """확인 권고 대상자 × 주. 가상 명부(D4, data/synthetic/roster_가상.csv)를 넣어 돌린 agent.py 표다."""
    path = APP / "agent_people.csv"
    return pd.read_csv(path, parse_dates=["기준일"], dtype={"행정동코드": str}) if path.exists() else None


@st.cache_data
def load_false_alarm(nomed: bool) -> pd.DataFrame:
    return pd.read_csv(REF / ("nomed_false_alarm.csv" if nomed else "false_alarm.csv"), index_col=0)


@st.cache_data
def load_weekly() -> pd.DataFrame:
    p = pd.read_csv(REF / "weekly_panel.csv")
    p["week"] = WEEK0 + pd.to_timedelta(p["w"] * 7, unit="D")
    return p


@st.cache_data
def load_shap() -> pd.DataFrame:
    return pd.read_csv(APP / "shap_weekly.csv")


@st.cache_data
def load_map() -> gpd.GeoDataFrame:
    return gpd.read_file(APP / "dong_map.geojson")


@st.cache_data
def load_facilities() -> pd.DataFrame:
    return pd.read_csv(APP / "facilities.csv")


def signed(x: float) -> str:
    r = int(round(x))
    return "0%" if r == 0 else f"{r:+d}%"


# ── ① 주간 브리핑 ──────────────────────────────────────────────────────
# agent.py(D1) 신호 넷. 색만으로 말하지 않고 항상 점·글자를 같이 단다
SIGNAL = {
    "빨강": ("빨강 · 필수형 끊김", CRITICAL),
    "주황": ("주황 · 대면형 끊김", SERIOUS),
    "노랑": ("노랑 · 좁아짐", WARNING),
    "초록": ("초록 · 평온", CALM),
}
SIGNAL_ORDER = {"빨강": 0, "주황": 1, "노랑": 2, "초록": 3}
DEMO_AS_OF = "2025-10-12"  # 시연 주 10/06~10/12 (#49 2번). 보조 장면 10/01 주황은 10/05 주


def next_action(r: pd.Series, n_same: int) -> str:
    """agent.py draft_outreach의 권고와 같은 순서 (07_에이전트 7.5, #2)."""
    if r["신호"] in ("빨강", "주황") and r["동시끊김"]:
        return f"공통 사건 먼저 확인 — 같은 도시 {n_same}개 집단 동시"
    if r["신호"] == "빨강":
        return "본인 전화 → 닿지 않으면 발길이 닿던 곳 → 방문 (복지서비스 후보)"
    if r["신호"] == "주황":
        return "본인 전화 → 닿지 않으면 발길이 닿던 곳"
    if r["신호"] == "노랑":
        return "동 단위 프로그램·봉사 일감 (사람이 아님)"
    return "—"


def screen_briefing():
    html(ui.heading("①", "주간 브리핑", "이번 주 누구를 먼저 확인할까 — 60대 이상 12개 집단, 보정 후 끊김 신호"))
    summ, groups = load_agent()
    days = list(summ["기준일"])
    as_of = st.select_slider("주 (월~일, 지난 7일 창)", options=days, value=pd.Timestamp(DEMO_AS_OF) if
                             pd.Timestamp(DEMO_AS_OF) in days else days[-1],
                             format_func=lambda d: f"{d - pd.Timedelta(days=6):%m/%d}~{d:%m/%d}")
    sm = summ[summ["기준일"] == as_of].iloc[0]
    g = groups[groups["기준일"] == as_of].copy()

    c = st.columns(4)
    n, n_prev = int(sm["확인권고_집단"]), int(sm["지난주_확인권고_집단"])
    c[0].markdown(ui.stat("확인 권고 집단", f"{n}", f"지난주 {n_prev}개 → {n - n_prev:+d}", unit="/ 12"),
                  unsafe_allow_html=True)
    c[1].markdown(ui.stat("빨강 · 필수형 끊김", f"{int(sm['빨강'])}", "필수 발길(장보기·병원·약국)까지", dot=CRITICAL),
                  unsafe_allow_html=True)
    c[2].markdown(ui.stat("주황 · 대면형 끊김", f"{int(sm['주황'])}", "대면 발길만", dot=SERIOUS), unsafe_allow_html=True)
    # 공통 충격 보정은 경보를 지우기도(명절) 드러내기도(30·40대는 그대로인데 고령만 준 주) 한다.
    # 그래서 "남은"이 아니라 "보정 뒤"로 부르고, 늘어난 주는 늘어났다고 적는다 (10/01 강남 남 60대 주황이 그 예)
    a0, a1, a2 = (int(sm[k]) for k in ("경보일_보정없음", "경보일_계절보정", "경보일_공통충격보정"))
    note = " · 보정으로 드러난 끊김" if a2 > a0 else ""
    c[3].markdown(ui.stat("보정 뒤 경보일", f"{a2}", f"집단 × 일 · 보정 없이 {a0} → 계절 {a1}{note}"),
                  unsafe_allow_html=True)

    st.write("")
    g["_o"] = g["신호"].map(SIGNAL_ORDER)
    same = g[g["동시끊김"]].groupby("도시").size()
    has_wx = "날씨가능" in g
    rows = []
    for _, r in g.sort_values(["_o", "집단"]).iterrows():
        label, color = SIGNAL[r["신호"]]
        broken = r["신호"] in ("빨강", "주황")
        rows.append({
            # 알림은 지우지 않고 꼬리표만 단다(B4 메모 4절). 상태 색이 아니라 글자로만 보인다
            "날씨 가능": ui.esc(re.sub(r"\([^)]*\)", "", r["궂은날"])) if has_wx and broken and r["날씨가능"] else "—",
            "신호": ui.badge(label, color),
            "집단": ui.esc(r["집단"]),
            "끊긴 날": f"{int(r['끊김일수'])}일" if broken else "—",
            "대면 발길 최저": signed(r["대면_7일최저_pct"]) if broken else "—",
            "필수 발길 최저": signed(r["필수_7일최저_pct"]) if broken else "—",
            "평소 닿던 업종": ui.esc(r["상대방업종"]) if broken else "—",
            # agent.py가 낸 문구를 그대로 쓴다(브리핑과 갈리지 않게). 열이 없는 옛 표에서만 화면 규칙으로
            "다음 행동": ui.esc(r["다음행동"] if r.get("다음행동") else next_action(r, int(same.get(r["도시"], 0)))),
            "_calm": r["신호"] == "초록",
        })
    cols = [("신호", ""), ("집단", ""), ("끊긴 날", "n"), ("대면 발길 최저", "n"), ("필수 발길 최저", "n")]
    cols += [("날씨 가능", "m")] if has_wx else []
    html(ui.table(cols + [("평소 닿던 업종", "m"), ("다음 행동", "m")], rows, dim_key="_calm"))
    st.caption("D1 agent.py 판정입니다(build_app_data.py가 매주 일요일 기준으로 돌린 표). 발길 변화는 지난 7일 창이고, "
               "계절·같은 도시 30·40대 공통 충격을 보정한 값입니다. 「날씨 가능」은 끊긴 창 안에 궂은 날(특보 기준 근사)이 있었다는 "
               "꼬리표이고, 알림을 지우지 않습니다. 노랑(좁아짐)은 6개월 평균이라 주마다 바뀌지 않습니다. "
               "「평소 닿던 업종」은 6개월 평소 결제가 몰린 업종이고, 실제 가게·경로당은 본인 등록으로만 정합니다.")
    st.write("")
    people_table(as_of, g)
    resource_lines(g)


# ── ② 발길 상세 ────────────────────────────────────────────────────────
N_DONG = {"강남": 22, "춘천": 25}  # 터전 순위의 분모 (도시 안 동 수)


def people_table(as_of: pd.Timestamp, g: pd.DataFrame):
    """끊긴 칸 × 가상 명부 → 이번 주 먼저 확인할 사람 (기획안 4절 0단계). 칸은 시군구 × 성 × 연령대이고,
    동은 대상자 주소에서만 붙인다. 이름·연락처는 표에도 없다(E6 4절)."""
    pp = load_people()
    if pp is None:
        return
    p = pp[pp["기준일"] == as_of]
    n_cell = g.set_index("집단")["명부_칸인원"] if "명부_칸인원" in g else pd.Series(dtype=float)
    html(f"<div class='bg-sec'>먼저 확인할 사람 {len(p)}명 <span style='color:{ui.MUTE};font-weight:400'>"
         "· 끊긴 칸마다 마지막 접촉이 오래된 3명 · <b>가상 명부</b>(41명, 실제 인물이 아닙니다)</span></div>")
    if p.empty:
        html(f"<div class='bg-callout'>이번 주에는 끊긴 집단이 없어 명부에서 올릴 사람이 없습니다. "
             "좁아짐(노랑)은 사람이 아니라 동 단위 자원으로 나갑니다.</div>")
        return
    order = g.set_index("집단")["신호"].map(SIGNAL_ORDER)
    p = p.assign(_o=p["집단"].map(order)).sort_values(["_o", "집단", "경과일"], ascending=[True, True, False])
    rows = []
    for _, r in p.iterrows():
        city = r["집단"].split()[0]
        label, color = SIGNAL[g.set_index("집단").loc[r["집단"], "신호"]]
        n = n_cell.get(r["집단"])
        rows.append({
            "신호": ui.badge(label.split(" · ")[0], color),
            "집단 (칸 인원)": ui.esc(r["집단"]) + (f" <span style='color:{ui.MUTE}'>({int(n)}명 중)</span>" if pd.notna(n) else ""),
            "대상자": ui.esc(r["대상자ID"]) + f" <span style='color:{ui.MUTE}'>{ui.esc(r['명부종류'])}</span>",
            "마지막 접촉": f"{int(r['경과일'])}일 전",
            "주소 동 · 터전 약한 순": f"{ui.esc(r['행정동'])} · {int(r['터전순위'])}/{N_DONG.get(city, '')}",
            "먼저 물을 창구": ui.esc(r["창구"]),
            "물어볼 곳 (후보 수)": ui.esc(re.sub(r"^(가게|경로당·마을회관) 먼저 — ", "", r["물어볼곳"])),
        })
    html(ui.table([("신호", ""), ("집단 (칸 인원)", ""), ("대상자", ""), ("마지막 접촉", "n"),
                   ("주소 동 · 터전 약한 순", ""), ("먼저 물을 창구", ""), ("물어볼 곳 (후보 수)", "m")], rows))
    st.caption("대상자·주소·접촉일은 모두 가상입니다(scripts/build_synthetic.py, 생성 방식은 E5 설계자료). "
               "발길 신호는 집단 단위이고, 동은 대상자 주소에서만 붙여 터전과 창구를 고릅니다 — 카드 지표를 동에 붙이지 않습니다. "
               "창구는 그 동의 상대방 업종 가게가 경로당·마을회관의 3배가 안 되면 경로당·마을회관을 먼저 묻습니다(10/17 확정 전 기준). "
               "후보 수는 상가·시설 공개 자료의 개수이고, 실제로 다니던 곳은 본인 등록으로만 받습니다.")


def resource_lines(g: pd.DataFrame):
    """이 주에 가져갈 것 — agent.py match_resource(#44)가 상태별로 고른 자원 후보 3개. 집단 단위라 같은 도시·같은
    신호면 같은 후보가 나오므로 묶어 한 줄씩 보인다. 사람에게 맞춘 추천이 아니다."""
    if "자원후보" not in g or not (g["자원후보"] != "").any():
        return
    kind = {"빨강": "방문 때 가져갈 복지서비스", "주황": "만남이 생기는 봉사·프로그램", "노랑": "동 단위로 나갈 봉사 일감"}
    shorten = lambda s: s if len(s) <= 34 else s[:33] + "…"  # noqa: E731  1365 제목이 길다
    lines, vol = [], False
    x = g[g["자원후보"] != ""].assign(_o=lambda d: d["신호"].map(SIGNAL_ORDER)).sort_values(["_o", "도시"])
    for (sig, city, res), d in x.groupby(["신호", "도시", "자원후보"], sort=False):
        label, color = SIGNAL[sig]
        items = " · ".join(ui.esc(shorten(s.strip())) for s in res.split(" · "))
        vol |= sig in ("주황", "노랑")
        lines.append(f"<div style='margin:4px 0;font-size:14px'>{ui.badge(label.split(' · ')[0], color)} "
                     f"<b>{ui.esc(city)}</b> {len(d)}개 집단 — {kind.get(sig, '')}: {items}</div>")
    html("<div class='bg-sec'>이 주에 가져갈 것 <span style='color:" + ui.MUTE + ";font-weight:400'>"
         "· 상태별 자원 후보 3개 (거리·반복성·만남 순, 규칙 정렬)</span></div>" + "".join(lines))
    st.caption("복지로 중앙·지자체 복지서비스(고령 대상만)와 1365 봉사 일감(모집 중만)에서 agent.py가 고른 후보입니다. "
               "집단 단위라 개인에게 맞춘 추천이 아니고, 실제 연결은 방문한 담당자가 판단합니다."
               + (" 1365 일감은 2026-10-14 수집 시점에 모집 중인 것이라 시연 기준일(2025년)의 일감이 아닙니다." if vol else ""))


def trend(df: pd.DataFrame, fields: dict[str, str], title: str, sub: str, wk: pd.Timestamp) -> alt.Chart:
    long = df.melt(id_vars=["week"], value_vars=list(fields), var_name="k", value_name="값")
    long["지표"] = long["k"].map(fields)
    names = list(fields.values())
    enc_color = alt.Color("지표:N", scale=alt.Scale(domain=names, range=SERIES[: len(names)]),
                          legend=alt.Legend(orient="bottom", title=None, direction="horizontal")
                          if len(names) > 1 else None)
    x = alt.X("week:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=6, grid=False))
    ln = alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=x, y=alt.Y("값:Q", title=None, axis=alt.Axis(tickCount=4)), color=enc_color,
        tooltip=[alt.Tooltip("week:T", title="주", format="%m/%d"), "지표:N", alt.Tooltip("값:Q", format="+.2f")])
    pt = alt.Chart(long[long["week"] == wk]).mark_point(size=80, filled=True, stroke=ui.CANVAS, strokeWidth=2,
                                                        opacity=1).encode(x="week:T", y="값:Q", color=enc_color)
    rule = alt.Chart(pd.DataFrame({"week": [wk]})).mark_rule(color=ui.MUTE, strokeDash=[3, 3]).encode(x="week:T")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#c9d3df").encode(y="y:Q")
    return (zero + rule + ln + pt).properties(title=alt.Title(title, subtitle=sub), height=200)


def screen_detail():
    html(ui.heading("②", "발길 상세", "왜 이 집단인가 — 양 · 질 · 연속성 · 터전 네 면과 모델의 근거"))
    p, s, m = load_weekly(), load_shap(), load_map()
    segs = sorted(s["seg"].unique())
    c1, c2 = st.columns([1, 2])
    seg = c1.selectbox("집단 (시군구 × 성 × 연령)", segs, index=segs.index("춘천 여성 80대"))
    weeks = sorted(s["w"].unique())
    w = c2.select_slider("주", options=weeks, value=weeks[-1],
                         format_func=lambda i: f"{(WEEK0 + pd.Timedelta(days=7 * int(i))):%m/%d}")
    wk = WEEK0 + pd.Timedelta(days=7 * int(w))
    g = p[p["seg"] == seg].sort_values("w")
    row = s[(s["seg"] == seg) & (s["w"] == w)].iloc[0]
    val = lambda f: float(g.loc[g["w"] == w, f].iloc[0])  # noqa: E731

    k = st.columns(4)
    k[0].markdown(ui.stat("다음 주 좁아짐 상위 진입 확률", f"{row['확률'] * 100:.0f}", "좁아짐 분류 모델", unit="%"),
                  unsafe_allow_html=True)
    k[1].markdown(ui.stat("양 · 발길 수", f"{val('breadth_z'):+.2f}", "같은 성·나이 기준 z"), unsafe_allow_html=True)
    k[2].markdown(ui.stat("질 · 체류 비중", f"{val('stay_z'):+.2f}", "같은 성·나이 기준 z"), unsafe_allow_html=True)
    k[3].markdown(ui.stat("연속성 · 3주 평균 좁아짐", f"{val('m3'):+.2f}", f"이번 주 {val('narrow'):+.2f}"),
                  unsafe_allow_html=True)
    st.write("")

    a, b = st.columns(2)
    with a, card("qty"):
        st.altair_chart(trend(g, {"breadth_z": "발길 수"}, "양 — 몇 곳에 닿는가", "유효 발길 수, 나이 보정 z", wk),
                        width="stretch")
    with b, card("qual"):
        st.altair_chart(trend(g, {"stay_z": "체류 비중"}, "질 — 얼굴을 아는 곳인가", "체류 업종 비중, 나이 보정 z", wk),
                        width="stretch")
    a, b = st.columns(2)
    with a, card("cont"):
        st.altair_chart(trend(g, {"narrow": "이번 주", "m3": "3주 평균"}, "연속성 — 늘 가던 대로 가는가",
                              "좁아짐 점수 (높을수록 좁아짐)", wk), width="stretch")
    city = seg.split()[0]
    weak = m[m["도시"] == city].sort_values("터전순위_통신").head(5)
    with b, card("ground"):
        html(f"<div class='bg-sec'>터전 — 닿을 곳이 있는가 <span style='color:{ui.MUTE};font-weight:400'>"
             f"· {city}, 동 단위</span></div>")
        html(ui.table([("동", ""), ("터전 순위", "n"), ("체류형 점포 /천명", "n"), ("경로당", "n")],
                      [{"동": ui.esc(r.ADM_NM), "터전 순위": f"{r.터전순위_통신}",
                        "체류형 점포 /천명": f"{r.체류형점포_천명당:.1f}", "경로당": f"{int(r.경로당수)}"}
                       for r in weak.itertuples()]))
        st.caption("단위가 다릅니다 — 양·질·연속성은 집단(시군구), 터전은 동. 카드 지표는 동에 붙이지 않습니다.")

    sv = pd.DataFrame({"변수": [FEATURE_KO[f] for f in FEATURE_KO], "기여": [row[f] for f in FEATURE_KO]})
    sv["방향"] = np.where(sv["기여"] >= 0, "확률을 높임", "확률을 낮춤")
    sv = sv.reindex(sv["기여"].abs().sort_values(ascending=False).index).head(6)
    span = float(sv["기여"].abs().max()) * 1.35
    lo, hi = (-span if (sv["기여"] < 0).any() else -span * 0.15), (span if (sv["기여"] > 0).any() else span * 0.15)
    bars = alt.Chart(sv).mark_bar(height=16, cornerRadiusEnd=4).encode(
        x=alt.X("기여:Q", title=None, axis=alt.Axis(format="+.2f", tickCount=5), scale=alt.Scale(domain=[lo, hi])),
        y=alt.Y("변수:N", sort=None, title=None,
                axis=alt.Axis(labelColor=ui.INK_2, labelFontSize=12, labelOverlap=False, labelLimit=160)),
        color=alt.Color("방향:N", scale=alt.Scale(domain=["확률을 높임", "확률을 낮춤"], range=[POS, NEG]),
                        legend=alt.Legend(orient="bottom", title=None, direction="horizontal")),
        tooltip=["변수:N", alt.Tooltip("기여:Q", format="+.3f")])
    lab = lambda df, align, dx: alt.Chart(df).mark_text(align=align, dx=dx, color=ui.INK_2, fontSize=11).encode(  # noqa: E731
        x="기여:Q", y=alt.Y("변수:N", sort=list(sv["변수"])), text=alt.Text("기여:Q", format="+.3f"))
    labels = lab(sv[sv["기여"] >= 0], "left", 6) + lab(sv[sv["기여"] < 0], "right", -6)
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#c9d3df").encode(x="x:Q")
    st.write("")
    left, right = st.columns([3, 2])
    with left, card("shap"):
        st.altair_chart((zero + bars + labels).properties(
            title=alt.Title("무엇이 확률을 움직였나", subtitle="집단 단위 기여도(SHAP) 상위 6개 — 터전 변수는 모델 입력에 없음"),
            height=240), width="stretch")
    with right, card("why"):
        html("<div class='bg-sec'>근거 문장</div>")
        html(f"<div class='bg-callout'>{ui.esc(seg)}의 {wk:%m/%d} 주 좁아짐 점수는 <b>{val('narrow'):+.2f}</b>, "
             f"3주 평균은 <b>{val('m3'):+.2f}</b>입니다. 체류 비중은 같은 성·나이 기준 <b>{val('stay_z'):+.2f}</b>, "
             f"발길 수는 <b>{val('breadth_z'):+.2f}</b>입니다. 다음 주 좁아짐 상위 7칸(32칸의 21.9%)에 들어갈 확률은 "
             f"<b>{row['확률'] * 100:.0f}%</b>입니다.</div>")
        st.caption("고정 문장 틀입니다(LLM 아님). 「병원·약국 비중」 막대는 집단 사이 수준이라 "
                   "\"병원·약국이 그 자리를 채운다\"(집단 안 시간 변화)와 나란히 읽지 않습니다. "
                   "모델: 재분석 b3 좁아짐 분류(랜덤포레스트, 32칸 × 25주). "
                   "양성 중 새로 들어온 칸은 31건뿐입니다 — 소표본입니다.")


# ── ③ 지도 ─────────────────────────────────────────────────────────────
METRICS = {
    "터전 점수 (통신)": ("터전점수_통신", "높을수록 터전이 강함"),
    "체류형 점포 (60세+ 천 명당)": ("체류형점포_천명당", "상가정보 · 커피·미용·목욕·운동·노래방·주점"),
    "경로당·마을회관 (60세+ 천 명당)": ("경로당_천명당", "표준데이터 · 공공이 노인 거주지에 배치"),
}


def screen_map():
    html(ui.heading("③", "터전 지도", "어느 동에 닿을 곳이 없나 — 47개 행정동 공급 지표와 시설"))
    m, fac = load_map(), load_facilities()
    c1, c2, c3 = st.columns([1, 2, 2])
    city = c1.radio("도시", ["춘천", "강남"], horizontal=True)
    label = c2.selectbox("색으로 볼 지표", list(METRICS))
    show = c3.multiselect("점으로 겹칠 시설", ["경로당", "도서관"], default=["경로당", "도서관"])
    col, hint = METRICS[label]
    g = m[m["도시"] == city].copy()
    sgg = "강원 춘천시" if city == "춘천" else "서울 강남구"

    q = pd.qcut(g[col], 5, labels=False, duplicates="drop")
    g["_c"] = [BLUE_RAMP[int(i)] for i in q]
    center = g.geometry.union_all().centroid
    fmap = folium.Map(location=[center.y, center.x], zoom_start=10 if city == "춘천" else 13,
                      tiles=None, control_scale=True)
    folium.TileLayer("Esri.WorldGrayCanvas", name="배경 지도", control=False).add_to(fmap)
    tip = folium.GeoJsonTooltip(
        fields=["ADM_NM", "터전순위_통신", "체류형점포_천명당", "경로당수", "도서관수", "인구_60세이상"],
        aliases=["동", "터전 순위(약한 순)", "체류형 점포 /60세+천명", "경로당·마을회관", "도서관", "60세+ 인구"],
        style=f"font-family:{ui.FONT};font-size:12px;color:{ui.INK};")
    folium.GeoJson(
        g.__geo_interface__,
        style_function=lambda f: {"fillColor": f["properties"]["_c"], "color": "#ffffff", "weight": 1.5,
                                  "fillOpacity": 0.88},
        highlight_function=lambda f: {"weight": 3, "color": ui.INK},
        tooltip=tip, name=label).add_to(fmap)
    for kind in show:
        layer = folium.FeatureGroup(name=kind)
        for r in fac[(fac["SGG_NM"] == sgg) & (fac["시설종류"] == kind)].itertuples():
            folium.CircleMarker([r.위도, r.경도], radius=4, color="#ffffff", weight=1.5, fill=True,
                                fill_color=FAC_COLOR[kind], fill_opacity=1,
                                tooltip=f"{kind} · {r.시설명} ({r.ADM_NM})").add_to(layer)
        layer.add_to(fmap)

    left, right = st.columns([3, 2])
    with left, card("map"):
        html(f"<div class='bg-sec'>{ui.esc(city)} · {ui.esc(label)} <span style='color:{ui.MUTE};font-weight:400'>"
             f"· {ui.esc(hint)}</span></div>")
        components.html(fmap.get_root().render(), height=500)
        lo, hi = g[col].min(), g[col].max()
        html(ui.legend([(f"{'낮음' if i == 0 else '높음' if i == 4 else ''}", c) for i, c in enumerate(BLUE_RAMP)]
                       + [(k, FAC_COLOR[k]) for k in show])
             .replace("<div class='bg-legend'>", f"<div class='bg-legend'><span>{lo:.1f}</span>", 1)
             .replace("</div>", f"<span>{hi:.1f} (5분위)</span></div>", 1))
    with right:
        k = st.columns(2)
        k[0].markdown(ui.stat("경로당·마을회관", f"{int(g['경로당수'].sum())}", f"{city} {len(g)}개 동", dot=FAC_COLOR["경로당"]),
                      unsafe_allow_html=True)
        k[1].markdown(ui.stat("도서관", f"{int(g['도서관수'].sum())}", "공공·작은·어린이", dot=FAC_COLOR["도서관"]),
                      unsafe_allow_html=True)
        st.write("")
        html(f"<div class='bg-sec'>{ui.esc(label)} 낮은 동 5곳</div>")
        t = g.sort_values(col).head(5)
        html(ui.table([("동", ""), ("값", "n"), ("터전 순위", "n"), ("경로당", "n"), ("60세+ 인구", "n")],
                      [{"동": ui.esc(r.ADM_NM), "값": f"{getattr(r, col):,.2f}".rstrip("0").rstrip("."),
                        "터전 순위": f"{r.터전순위_통신}", "경로당": f"{int(r.경로당수)}",
                        "60세+ 인구": f"{int(r.인구_60세이상):,}"} for r in t.itertuples()]))
        st.write("")
        html("<div class='bg-callout'>체류형 점포와 경로당은 <b>방향이 반대</b>입니다(춘천 스피어만 −0.79). "
             "면 지역은 가게가 적은 대신 노인 인구 대비 경로당이 많아, 한 지수로 더하지 않고 따로 봅니다(#6).</div>")
        st.caption("사회복지시설은 공개 데이터에 좌표가 없어 넣지 않았습니다.")


# ── ④ 보정 전·후 ───────────────────────────────────────────────────────
STEPS = {"보정 없음": "(0) 보정 없음", "계절형 보정": "(1) 계절형 보정", "+ 공통 충격 보정": "(2) + 공통 충격 보정"}
STEP_COL = {"보정 없음": "al0", "계절형 보정": "al1", "+ 공통 충격 보정": "al2"}


def screen_correction():
    html(ui.heading("④", "보정 전·후", "헛알림을 얼마나 지웠나 — 명절·공휴일처럼 모두가 함께 줄어드는 날을 먼저 지운다"))
    c1, c2 = st.columns([3, 2])
    step = c1.radio("보정 단계", list(STEPS), index=0, horizontal=True)
    nomed = c2.toggle("병원·약국을 필수 발길에서 분리", value=False)
    b, fa = load_breaks(nomed), load_false_alarm(nomed)
    base, cur = fa.loc["(0) 보정 없음"], fa.loc[STEPS[step]]
    is_base = step == "보정 없음"

    k = st.columns(3)
    k[0].markdown(ui.stat("전체 알림", f"{int(cur['전체 알림'])}", "집단 × 일" if is_base else
                          f"보정 없음 {int(base['전체 알림'])}에서 {int(cur['전체 알림'] - base['전체 알림']):+d}"),
                  unsafe_allow_html=True)
    k[1].markdown(ui.stat("공통 사건 주간 알림", f"{int(cur.iloc[1])}", "추석·광복절·성탄 뒤 7일" if is_base else
                          f"보정 없음 {int(base.iloc[1])}에서 {int(cur.iloc[1] - base.iloc[1]):+d}", dot=CRITICAL),
                  unsafe_allow_html=True)
    k[2].markdown(ui.stat("공통 사건 주간 감소율", f"{(1 - cur.iloc[1] / base.iloc[1]) * 100:.0f}", "보정 없음 대비",
                          unit="%"), unsafe_allow_html=True)
    st.write("")

    d = b[["date", "seg", "holwk", STEP_COL[step]]].rename(columns={STEP_COL[step]: "alert"})
    spans = (b[b["holwk"]].drop_duplicates("date")[["date"]]
             .assign(g=lambda x: (x["date"].diff().dt.days != 1).cumsum())
             .groupby("g")["date"].agg(["min", "max"]).reset_index(drop=True))
    spans["max"] = spans["max"] + pd.Timedelta(days=1)
    domain = [b["date"].min().isoformat(), (b["date"].max() + pd.Timedelta(days=1)).isoformat()]
    order = sorted(d["seg"].unique())
    shade = alt.Chart(spans).mark_rect(color=SHADE).encode(x=alt.X("min:T", scale=alt.Scale(domain=domain)), x2="max:T")
    rows = alt.Chart(d).mark_tick(opacity=0).encode(y=alt.Y("seg:N", sort=order, title=None,
                                                            axis=alt.Axis(labelColor=ui.INK_2, labelFontSize=12)))
    cells = alt.Chart(d[d["alert"]]).mark_rect(color=CRITICAL, cornerRadius=2).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=12, grid=False),
                scale=alt.Scale(domain=domain)),
        x2=alt.X2("end:T"), y=alt.Y("seg:N", sort=order),
        tooltip=[alt.Tooltip("date:T", title="날짜", format="%Y-%m-%d"), alt.Tooltip("seg:N", title="집단")],
    ).transform_calculate(end="datetime(year(datum.date), month(datum.date), date(datum.date) + 1)")
    with card("heat"):
        st.altair_chart((shade + rows + cells).properties(
            title=alt.Title("집단 × 날짜 알림", subtitle=f"{step}{' · 병원·약국 분리' if nomed else ''} — 빨간 칸이 끊김 판정"),
            height=330), width="stretch")
        html(ui.legend([("알림 (끊김 판정)", CRITICAL), ("공통 사건 주간 (추석·광복절·성탄 뒤 7일)", SHADE)]))
    st.caption("보정을 끄면 추석 주간이 알림으로 뒤덮입니다. 계절형 보정만으로는 줄지 않고, 같은 도시 30·40대가 함께 "
               "줄어든 만큼을 빼는 공통 충격 보정에서 크게 줄어듭니다. 출처: 재분석 b2 (reanalysis/reference/false_alarm.csv).")
    st.write("")
    html("<div class='bg-sec'>보정 단계별 알림 수</div>")
    html(ui.table([("보정 단계", ""), ("전체 알림", "n"), ("공통 사건 주간", "n"), ("그 밖의 날", "n"), ("공통 사건 주간 감소율", "n")],
                  [{"보정 단계": ui.esc(i), "전체 알림": f"{int(r.iloc[0])}", "공통 사건 주간": f"{int(r.iloc[1])}",
                    "그 밖의 날": f"{int(r.iloc[2])}", "공통 사건 주간 감소율": f"{r.iloc[3]:.0f}%"} for i, r in fa.iterrows()]))


# ── 화면 ───────────────────────────────────────────────────────────────
html(ui.hero("발길", "담당자 화면", "집단 지표는 실제 분석 결과(신한카드·SK·상가·공공데이터)이고, 개인 단위 사례는 모두 "
             "<b>가상</b>입니다. 수치는 10/17 동결 뒤 최종수치표 값으로 바뀝니다.", "시연용"))
SCREENS = {"① 주간 브리핑": screen_briefing, "② 발길 상세": screen_detail, "③ 터전 지도": screen_map,
           "④ 보정 전·후": screen_correction}
only = st.query_params.get("screen")  # ?screen=1~4 → 그 화면만 (캡처·데모용)
if only in {"1", "2", "3", "4"}:
    list(SCREENS.values())[int(only) - 1]()
else:
    for tab, draw in zip(st.tabs(list(SCREENS)), SCREENS.values()):
        with tab:
            draw()
