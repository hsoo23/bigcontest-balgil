"""발길 — 담당자 화면 4개 (D3, 시연용).

실행: streamlit run app/balgil_app.py      (?screen=1~4 를 붙이면 그 화면만 — 캡처·데모용)
의존: app/requirements-app.txt (분석 쪽 requirements.txt에 화면 라이브러리를 더한 것)

읽는 파일은 모두 git에 있다 — 원본 데이터가 없어도 뜬다.
  reanalysis/reference/   재분석 결과 (끊김·보정·주간 패널)
  data/reference/app/     scripts/build_app_data.py가 만든 지도·시설·SHAP

원칙
  * 집단 지표(양·질·연속성)는 시군구 × 성 × 연령까지만. 동 단위로 보여 주는 것은 터전뿐이다.
  * 신호등 5단계와 끊김 종류(대면형·장보기형·병원약국형)는 D1 agent.py가 나오면 바꾼다.
    지금은 재분석 b2의 주황(대면만 끊김)·빨강(필수까지 끊김)을 그대로 보인다.
  * 숫자는 10/17 수치 동결 뒤 docs/최종수치표.md 값으로 교체한다.

겉모양은 app/style.py(Stripe DESIGN.md 토큰). 데이터 색은 dataviz 기준 팔레트(검증: validate_palette.js)
  상태(주황·빨강)   status serious/critical — 색만으로 말하지 않고 항상 점·글자를 같이 단다
  터전 지도         순차 파랑 한 가지 (진할수록 값이 큼)
  지도 위 시설 점   주황(경로당)·청록(도서관) — 범주 2·3번, 전 쌍 CVD ΔE 9.2 통과
  SHAP 막대         발산 파랑(확률을 낮춤)·빨강(높임)
"""
from __future__ import annotations

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
SERIOUS, CRITICAL, CALM = "#ec835a", "#d03b3b", "#c3ccd7"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"]  # 순차 100·250·400·500·650
POS, NEG = "#e34948", "#2a78d6"  # 발산: 확률을 높임 / 낮춤
SERIES = ["#2a78d6", "#eb6834"]  # 범주 1·2번 (선 두 개)
FAC_COLOR = {"경로당": "#eb6834", "도서관": "#1baf7a"}
SHADE = "#eef2f7"  # 공통 사건 주간 배경 띠

STATE = {
    "빨강(필수까지 끊김)": ("빨강", "필수까지 끊김", CRITICAL),
    "주황(대면만 끊김)": ("주황", "대면만 끊김", SERIOUS),
    "-": ("평온", "", CALM),
}
ORDER = {"빨강(필수까지 끊김)": 2, "주황(대면만 끊김)": 1, "-": 0}
NEXT_ACTION = "본인 전화 → 닿지 않으면 단골 확인"  # 다섯 마디 4번 (#2)

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
def screen_briefing():
    html(ui.heading("①", "주간 브리핑", "이번 주 누구를 먼저 확인할까 — 60대 이상 12개 집단, 보정 후 끊김 신호"))
    b = load_breaks(nomed=False)
    weeks = sorted(b["week"].unique())
    hol_weeks, alert_weeks = set(b.loc[b["holwk"], "week"]), set(b.loc[b["state"] != "-", "week"])
    default = max(w for w in weeks if w not in hol_weeks and w in alert_weeks)
    wk = st.select_slider("주 (월요일 시작)", options=weeks, value=default,
                          format_func=lambda d: f"{pd.Timestamp(d):%m/%d}")
    cur, prev = b[b["week"] == wk], b[b["week"] == wk - pd.Timedelta(days=7)]
    worst = lambda df: df.groupby("seg")["state"].agg(lambda s: max(s, key=ORDER.get))  # noqa: E731
    w_now = worst(cur)
    n_prev = int((worst(prev) != "-").sum()) if len(prev) else None
    flagged = int((w_now != "-").sum())

    c = st.columns(4)
    diff = "" if n_prev is None else (f"지난주 {n_prev}개 → {'+' if flagged >= n_prev else ''}{flagged - n_prev}")
    c[0].markdown(ui.stat("확인 권고 집단", f"{flagged}", diff, unit="/ 12"), unsafe_allow_html=True)
    c[1].markdown(ui.stat("빨강 · 필수까지 끊김", f"{int((w_now == '빨강(필수까지 끊김)').sum())}", "집단 수",
                          dot=CRITICAL), unsafe_allow_html=True)
    c[2].markdown(ui.stat("주황 · 대면만 끊김", f"{int((w_now == '주황(대면만 끊김)').sum())}", "집단 수",
                          dot=SERIOUS), unsafe_allow_html=True)
    c[3].markdown(ui.stat("끊긴 날", f"{int((cur['state'] != '-').sum())}", "집단 × 일 (보정 후 남은 알림)"),
                  unsafe_allow_html=True)

    st.write("")
    rows = []
    for seg, state in sorted(w_now.items(), key=lambda kv: (-ORDER[kv[1]], kv[0])):
        g = cur[cur["seg"] == seg]
        name, desc, color = STATE[state]
        rows.append({
            "신호": ui.badge(name + (f" · {desc}" if desc else ""), color),
            "집단": ui.esc(seg),
            "끊긴 날": f"{int((g['state'] != '-').sum())}일",
            "대면 발길 최저": signed(g["face_pct"].min()),
            "필수 발길 최저": signed(g["ess_pct"].min()),
            "다음 행동": NEXT_ACTION if state != "-" else "—",
            "_calm": state == "-",
        })
    html(ui.table([("신호", ""), ("집단", ""), ("끊긴 날", "n"), ("대면 발길 최저", "n"),
                   ("필수 발길 최저", "n"), ("다음 행동", "m")], rows, dim_key="_calm"))
    st.caption("발길 변화는 7일 묶음이고, 계절·같은 도시 30·40대 공통 충격을 보정한 값입니다. "
               "신호 5단계와 끊김 종류(대면형·장보기형·병원약국형)는 D1 agent.py가 나오면 바뀝니다.")


# ── ② 발길 상세 ────────────────────────────────────────────────────────
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
             f"발길 수는 <b>{val('breadth_z'):+.2f}</b>입니다. 다음 주 좁아짐 상위 20%에 들어갈 확률은 "
             f"<b>{row['확률'] * 100:.0f}%</b>입니다.</div>")
        st.caption("고정 문장 틀입니다(LLM 아님). 「병원·약국 비중」 막대는 집단 사이 수준이라 "
                   "\"병원·약국이 그 자리를 채운다\"(집단 안 시간 변화)와 나란히 읽지 않습니다. "
                   "모델: 재분석 b3 좁아짐 분류(랜덤포레스트, 32칸 × 25주).")


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
