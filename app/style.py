"""화면 겉모양 — Stripe DESIGN.md(awesome-design-md)를 따른 토큰과 HTML 조각.

크롬(바탕·글자·카드·탭)만 Stripe 토큰을 쓴다. 데이터 색(신호·지도·차트)은 balgil_app.py의
dataviz 검증 팔레트를 그대로 둔다 — 색각 이상 검증을 통과한 색만 데이터에 쓴다.

Stripe 원칙 중 가져온 것
  * 글자는 순검정이 아니라 짙은 남색 ink(#0d253d), 보조는 ink-mute(#64748d)
  * 남보라 primary(#533afd)는 선택·강조에만 아껴 쓴다 (한 화면에 채운 요소 하나)
  * 숫자 칸은 표 숫자(tnum) + 살짝 좁힌 자간
  * 카드: 흰 바탕, 1px hairline(#e3e8ee), 12px 모서리, 아주 옅은 그림자(level 1)
  * 위쪽에만 그라데이션 띠 — 이 브랜드의 깊이 표현
글꼴: Sohne는 한글이 없어 Pretendard(Inter 계열 한글)로 대신한다.
"""
from __future__ import annotations

import html

INK, INK_2, MUTE = "#0d253d", "#273951", "#64748d"
CANVAS, CANVAS_SOFT, HAIRLINE = "#ffffff", "#f6f9fc", "#e3e8ee"
PRIMARY, PRIMARY_DEEP, PRIMARY_SOFT_BG = "#533afd", "#4434d4", "#ecebff"
BRAND_DARK = "#1c1e54"
FONT = "'Pretendard Variable', Pretendard, -apple-system, 'SF Pro Display', system-ui, sans-serif"

CSS = f"""
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css");
html, body, [class*="st-"], .stApp, button, input, textarea, select {{
  font-family: {FONT} !important; color: {INK};
  font-feature-settings: "ss01";
}}
.stApp {{ background: {CANVAS_SOFT}; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: "Material Symbols Rounded" !important; }}
iframe {{ border-radius: 8px; }}
[data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display: none !important; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 48px; max-width: 1280px; }}

/* 위쪽 그라데이션 띠 + 헤더 */
.bg-hero {{
  margin: 0 -9999px 28px; padding: 28px 9999px 22px;
  background:
    radial-gradient(60% 140% at 8% 0%, rgba(245,233,212,.95) 0%, rgba(245,233,212,0) 60%),
    radial-gradient(45% 160% at 38% 0%, rgba(185,185,249,.75) 0%, rgba(185,185,249,0) 62%),
    radial-gradient(40% 160% at 68% 0%, rgba(83,58,253,.35) 0%, rgba(83,58,253,0) 60%),
    radial-gradient(35% 150% at 95% 0%, rgba(234,34,97,.22) 0%, rgba(234,34,97,0) 60%),
    {CANVAS_SOFT};
  border-bottom: 1px solid {HAIRLINE};
}}
.bg-brand {{ display:flex; align-items:baseline; gap:12px; }}
.bg-mark {{ font-size: 30px; font-weight: 600; letter-spacing: -0.6px; color: {INK}; }}
.bg-sub {{ font-size: 15px; font-weight: 400; color: {INK_2}; }}
.bg-note {{ margin-top: 8px; font-size: 13px; color: {MUTE}; letter-spacing: -0.2px; }}
.bg-pill {{ display:inline-block; padding: 3px 10px; border-radius: 9999px; background: {PRIMARY_SOFT_BG};
  color: {PRIMARY_DEEP}; font-size: 12px; font-weight: 500; margin-left: 6px; vertical-align: 2px; }}

/* 탭 */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {HAIRLINE}; }}
.stTabs [data-baseweb="tab"] {{ height: 44px; padding: 0 14px; color: {MUTE}; font-size: 15px; }}
.stTabs [aria-selected="true"] {{ color: {INK} !important; font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {PRIMARY} !important; height: 2px; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* 화면 제목 */
.bg-h {{ font-size: 26px; font-weight: 300; letter-spacing: -0.4px; color: {INK}; margin: 18px 0 2px; }}
.bg-h b {{ font-weight: 600; }}
.bg-lead {{ font-size: 14px; color: {MUTE}; margin-bottom: 16px; }}
.bg-sec {{ font-size: 15px; font-weight: 600; color: {INK}; margin: 4px 0 8px; letter-spacing: -0.2px; }}

/* 카드 */
div[data-testid="stVerticalBlockBorderWrapper"][data-test-border="true"],
div.st-key-card, div[class*="st-key-card"] {{
  background: {CANVAS}; border: 1px solid {HAIRLINE} !important; border-radius: 12px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; padding: 20px 22px;
}}
.bg-stat {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px; padding:16px 20px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; height: 100%; }}
.bg-stat .l {{ font-size:13px; color:{MUTE}; letter-spacing:-0.2px; display:flex; align-items:center; gap:6px; }}
.bg-stat .v {{ font-size:32px; font-weight:300; letter-spacing:-0.8px; color:{INK};
  font-feature-settings:"tnum"; margin-top:6px; line-height:1.1; }}
.bg-stat .v small {{ font-size:16px; color:{MUTE}; font-weight:400; letter-spacing:0; }}
.bg-stat .d {{ font-size:12px; color:{MUTE}; margin-top:6px; font-feature-settings:"tnum"; }}
.bg-dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; }}

/* 표 */
.bg-table {{ width:100%; border-collapse:separate; border-spacing:0; background:{CANVAS};
  border:1px solid {HAIRLINE}; border-radius:12px; overflow:hidden; box-shadow: rgba(0,55,112,0.08) 0 1px 3px; }}
.bg-table th {{ text-align:left; font-size:12px; font-weight:500; color:{MUTE}; padding:10px 14px;
  background:{CANVAS_SOFT}; border-bottom:1px solid {HAIRLINE}; letter-spacing:-0.1px; }}
.bg-table td {{ font-size:14px; color:{INK}; padding:10px 14px; border-bottom:1px solid {HAIRLINE}; }}
.bg-table tr:last-child td {{ border-bottom:none; }}
.bg-table td.n, .bg-table th.n {{ text-align:right; font-feature-settings:"tnum"; letter-spacing:-0.3px; }}
.bg-table td.m {{ color:{MUTE}; font-size:13px; }}
.bg-table tr.dim td {{ color:{MUTE}; }}
.bg-badge {{ display:inline-flex; align-items:center; gap:6px; padding:2px 10px 2px 8px; border-radius:9999px;
  font-size:12.5px; font-weight:500; border:1px solid {HAIRLINE}; background:{CANVAS}; white-space:nowrap; }}

/* 입력 위젯 */
[data-testid="stWidgetLabel"] p {{ font-size: 13px !important; color: {MUTE} !important; }}
div[data-baseweb="select"] > div {{ border-radius: 8px; border-color: {HAIRLINE}; background:{CANVAS}; }}
[data-testid="stSlider"] [role="slider"] {{ background: {PRIMARY} !important; box-shadow: none !important; }}
[data-testid="stSlider"] div[data-testid="stSliderTickBarMin"],
[data-testid="stSlider"] div[data-testid="stSliderTickBarMax"] {{ color: {MUTE}; }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: {MUTE} !important; font-size: 12.5px !important; line-height: 1.55; }}
[data-testid="stExpander"] details {{ border-radius: 12px; border-color: {HAIRLINE}; background: {CANVAS}; }}
hr {{ border-color: {HAIRLINE} !important; }}
.bg-legend {{ font-size:12px; color:{MUTE}; display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin-top:8px; }}
.bg-legend i {{ display:inline-block; width:14px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }}
.bg-callout {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-left:3px solid {PRIMARY}; border-radius:8px;
  padding:12px 14px; font-size:13.5px; color:{INK_2}; line-height:1.6; }}
</style>
"""


def esc(x) -> str:
    return html.escape(str(x))


def hero(title: str, sub: str, note: str, pill: str) -> str:
    return (f"<div class='bg-hero'><div class='bg-brand'><span class='bg-mark'>{esc(title)}</span>"
            f"<span class='bg-sub'>{esc(sub)}</span><span class='bg-pill'>{esc(pill)}</span></div>"
            f"<div class='bg-note'>{note}</div></div>")


def heading(num: str, title: str, lead: str) -> str:
    return f"<div class='bg-h'><b>{esc(num)}</b> {esc(title)}</div><div class='bg-lead'>{esc(lead)}</div>"


def stat(label: str, value: str, sub: str = "", dot: str | None = None, unit: str = "") -> str:
    d = f"<span class='bg-dot' style='background:{dot}'></span>" if dot else ""
    u = f" <small>{esc(unit)}</small>" if unit else ""
    s = f"<div class='d'>{sub}</div>" if sub else ""
    return f"<div class='bg-stat'><div class='l'>{d}{esc(label)}</div><div class='v'>{esc(value)}{u}</div>{s}</div>"


def badge(text: str, color: str) -> str:
    return f"<span class='bg-badge'><span class='bg-dot' style='background:{color}'></span>{esc(text)}</span>"


def table(columns: list[tuple[str, str]], rows: list[dict], dim_key: str | None = None) -> str:
    """columns: [(제목, 'n'=숫자 오른쪽 정렬 | 'm'=흐린 글자 | '')]. 값에 HTML을 넣으려면 미리 만들어 둔다."""
    head = "".join(f"<th class='{c}'>{esc(t)}</th>" for t, c in columns)
    body = []
    for r in rows:
        cls = " class='dim'" if dim_key and r.get(dim_key) else ""
        body.append(f"<tr{cls}>" + "".join(f"<td class='{c}'>{r[t]}</td>" for t, c in columns) + "</tr>")
    return f"<table class='bg-table'><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def legend(items: list[tuple[str, str]]) -> str:
    return "<div class='bg-legend'>" + "".join(f"<span><i style='background:{c}'></i>{esc(t)}</span>"
                                                for t, c in items) + "</div>"
