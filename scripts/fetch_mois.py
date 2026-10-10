"""행정안전부 주민등록 통계를 받는다 — 누가 다시 돌려도 같은 파일이 나오게.

대회 규정은 외부 데이터에 대해 **출처와 수집 방법을 명시하고 활용한 원본 파일을
제출**하도록 요구한다. 화면에서 손으로 받으면 조회 조건이 기록으로 남지 않으므로,
조건을 코드에 적어 두고 그대로 요청한다. 브라우저에서 내려받기를 누르는 것과
같은 요청이고 로그인·인증키가 없는 공개 통계다.

받는 것 (2025년 12월, 행정동, 1세 단위, 계·남·여, 등록구분 전체)
  mois_single_household : 행정동별 성/연령별 주민등록 1인세대수  → 1인세대율의 분자
  mois_population       : 행정동별 연령별 인구현황              → 분모

원본은 가공하지 않고 `data/external/<슬러그>/`에 그대로 둔다. 받은 뒤
`python scripts/register_external.py`를 돌리면 SHA-256까지 기록된다.

실행: python scripts/fetch_mois.py
"""
from __future__ import annotations

import http.cookiejar
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balgil.data import ROOT

BASE = "https://jumin.mois.go.kr"
EXTERNAL_DIR = ROOT / "data" / "external"

# 조회 조건 — 이 값이 곧 수집 방법의 기록이다.
YEAR, MONTH = "2025", "12"      # 분석 기간(2025-07~12)의 끝. 이 통계표는 검색기간이 1개월로 제한된다
AGE_UNIT = "1"                  # 1세 단위. 10세로 받으면 60~69로 묶여 65세+를 뽑을 수 없다
AGE_FROM, AGE_TO = "0", "100"   # 전체 범위. 65세+만 받으면 비중의 분모와 30·40대가 없어진다
REGIST_TYPE = ""                # 등록구분 전체

REGIONS = {  # 슬러그에 쓸 이름: (시도 코드, 시군구 코드)
    "강남구": ("1100000000", "1168000000"),
    "춘천시": ("5100000000", "5111000000"),
}

SOURCES = {
    "mois_single_household": {
        "page": f"{BASE}/sexdAge1Hshd.do?sttsGbn=admm",
        "down": f"{BASE}/sexdAge1HshdDown.do?searchYearMonth=month&xlsStats=1&downType=Csv",
        "extra": {"sttsGbn": "admm"},
        "name": "행정동별_성연령별_1인세대수",
    },
    "mois_population": {
        "page": f"{BASE}/ageStatMonth.do",
        "down": f"{BASE}/downloadCsvAge.do?searchYearMonth=month&xlsStats=1",
        "extra": {"sltOrgType": "2", "sltOrderType": "1", "sltOrderValue": "ASC"},
        "name": "행정동별_연령별_인구현황",
    },
}


def fetch(slug: str, spec: dict) -> None:
    """표준 라이브러리만 쓴다 — requirements.txt는 회의에서 함께 올리는 파일이다."""
    folder = EXTERNAL_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    opener.open(spec["page"], timeout=30).read()  # 세션 쿠키

    for region, (lvl1, lvl2) in REGIONS.items():
        form = [
            ("sltOrgLvl1", lvl1), ("sltOrgLvl2", lvl2), ("sltUndefType", REGIST_TYPE),
            ("searchYearStart", YEAR), ("searchMonthStart", MONTH),
            ("searchYearEnd", YEAR), ("searchMonthEnd", MONTH),
            ("sltArgTypes", AGE_UNIT), ("sltArgTypeA", AGE_FROM), ("sltArgTypeB", AGE_TO),
            ("sum", "sum"), ("gender", "gender"), ("category", "month"),
            ("state", "1"), ("state", "2"), ("state", "3"),  # 계·남·여
            *spec["extra"].items(),
        ]
        req = urllib.request.Request(
            spec["down"],
            data=urllib.parse.urlencode(form).encode(),
            headers={"Referer": spec["page"]},
        )
        body = opener.open(req, timeout=60).read()
        dest = folder / f"{YEAR}{MONTH}_{spec['name']}_{region}.csv"
        dest.write_bytes(body)
        print(f"  {dest.relative_to(ROOT)}  {len(body):,}B")


def main() -> None:
    for slug, spec in SOURCES.items():
        print(f"[{slug}] {spec['page']}")
        fetch(slug, spec)
    print("\n받았습니다. 이어서 `python scripts/register_external.py`로 출처를 기록하세요.")


if __name__ == "__main__":
    main()
