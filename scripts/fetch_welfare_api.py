"""공공데이터포털 API로 에이전트가 추천할 자원 데이터를 수집한다.

수집 대상
  welfare_central : 한국사회보장정보원 중앙부처복지서비스 (전국)
  welfare_local   : 한국사회보장정보원 지자체복지서비스 (강남구·춘천시)
  volunteer_1365  : 행정안전부 봉사참여정보서비스_GW (서울·강원)

인증키는 .env의 DATA_GO_KR_KEY에서 읽는다. 키 값은 로그에 출력하지 않는다.
원본 응답(XML)은 data/external/<슬러그>/raw/에 그대로 보관한다. 대회 규정상
활용한 원본 파일을 제출해야 하기 때문이다.

실행: python scripts/fetch_welfare_api.py              API로 받아 원본 XML과 정제본을 새로 만든다 (키 필요)
      python scripts/fetch_welfare_api.py --from-raw   올려 둔 원본 XML만 읽어 정제본을 다시 만든다 (키 없이, 재현용)
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

EXTERNAL_DIR = ROOT / "data" / "external"
PAGE_SIZE = 100
SLEEP = 0.2  # 호출 간격

# 1365 지역코드(행정기관코드). 시군구 코드는 수집 결과의 기관명에서 확인했다.
SIDO = {"6110000": "서울특별시", "6420000": "강원특별자치도"}
GUGUN = {"3220000": "서울 강남구", "4180000": "강원 춘천시"}

SOURCES = {
    "welfare_central": {
        "name": "한국사회보장정보원_중앙부처복지서비스",
        "url": "https://www.data.go.kr/data/15090532/openapi.do",
        "endpoint": "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001",
        "spatial_unit": "전국(지역 구분 없음)",
    },
    "welfare_local": {
        "name": "한국사회보장정보원_지자체복지서비스",
        "url": "https://www.data.go.kr/data/15108347/openapi.do",
        "endpoint": "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist",
        "spatial_unit": "시군구",
    },
    "volunteer_1365": {
        "name": "행정안전부_봉사참여정보서비스_GW",
        "url": "https://www.data.go.kr/data/15157582/openapi.do",
        "endpoint": "https://apis.data.go.kr/1741000/volunteerPartcptnService/getVltrAreaList",
        "spatial_unit": "시도·시군구 코드",
    },
}


def load_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and "KEY" in line.split("=")[0].upper():
            return line.split("=", 1)[1].strip()
    raise SystemExit(".env에 DATA_GO_KR_KEY가 없습니다. docs/데이터_수집_가이드.md를 참고하세요.")


def request(endpoint: str, params: dict, key: str, retries: int = 5) -> str:
    query = urllib.parse.urlencode(params, encoding="utf-8") + "&serviceKey=" + urllib.parse.quote(key, safe="")
    # 포털이 가끔 응답하지 않거나 resultCode 99를 준다(10/14 시험에서 다섯 번에 한 번꼴). 잠시 쉬고 다시 묻는다
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f"{endpoint}?{query}", timeout=60) as resp:
                body = resp.read().decode("utf-8", "replace")
            # 포털 오류(예: resultCode 99 UNKNOWN_ERROR)는 totalCount 0으로 와서 0건으로 착각하기 쉽다
            code = re.search(r"<resultCode>\s*(\w+)\s*<", body)
            if code and code.group(1) not in ("0", "00"):
                raise urllib.error.URLError(f"resultCode {code.group(1)}")
            return body
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise
            print(f"  응답 실패({e}) — {5 * (attempt + 1)}초 뒤 다시 시도")
            time.sleep(5 * (attempt + 1))


def fetch_all(slug: str, params: dict, key: str | None, tag: str, label: str) -> pd.DataFrame:
    """페이지를 끝까지 돌며 수집하고 원본 XML을 보관한다. key가 None이면 API 대신 보관한 원본을 읽는다."""
    src = SOURCES[slug]
    raw_dir = EXTERNAL_DIR / slug / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows, page, total = [], 1, None
    while True:
        path = raw_dir / f"{label}_p{page:03d}.xml"
        if key is None:
            if not path.exists():
                raise SystemExit(f"원본이 없습니다: {path.relative_to(ROOT)} — 키로 한 번 수집해야 합니다")
            body = path.read_text(encoding="utf-8")
        else:
            body = request(src["endpoint"], {**params, "pageNo": str(page), "numOfRows": str(PAGE_SIZE)}, key)
            path.write_text(body, encoding="utf-8")

        if total is None:
            match = re.search(r"totalCount>\s*(\d+)", body)
            total = int(match.group(1)) if match else 0
        # 원본에 공백 대신 제어문자(\x01)가 섞인 페이지가 있다(1365 서울 24페이지). 원본은 그대로 두고 읽을 때만 공백으로 바꾼다
        items = ElementTree.fromstring(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", body)).iter(tag)
        page_rows = [{child.tag: (child.text or "").strip() for child in item} for item in items]
        rows.extend(page_rows)

        if not page_rows or len(rows) >= total:
            break
        page += 1
        if key is not None:
            time.sleep(SLEEP)

    print(f"  {label}: {len(rows):,}건 (totalCount {total:,}, {page}페이지)")
    return pd.DataFrame(rows)


def write_meta(slug: str, note: str) -> None:
    src = SOURCES[slug]
    meta = {
        "name": src["name"],
        "provider": src["name"].split("_")[0],
        "url": src["url"],
        "collected_at": date.today().isoformat(),
        "reference_date": date.today().isoformat(),
        "spatial_unit": src["spatial_unit"],
        "license": "이용허락범위 제한 없음",
        "free": True,
        "note": note,
    }
    (EXTERNAL_DIR / slug / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--from-raw", action="store_true", help="API를 부르지 않고 data/external/<슬러그>/raw/ 원본만 읽는다")
    from_raw = ap.parse_args().from_raw
    key = None if from_raw else load_key()
    if from_raw:  # 수집일이 바뀌지 않게 meta.json은 건드리지 않는다
        global write_meta
        write_meta = lambda *_: None  # noqa: E731
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("■ 중앙부처 복지서비스")
    central = fetch_all("welfare_central", {"callTp": "L", "srchKeyCode": "003"}, key, "servList", "central")
    central.to_parquet(PROCESSED_DIR / "res_welfare_central.parquet", index=False)
    write_meta("welfare_central", "복지로 중앙부처 복지서비스 목록. API 활용신청 후 인증키로 수집")

    print("■ 지자체 복지서비스")
    local = pd.concat(
        [
            fetch_all("welfare_local", {"ctpvNm": ctpv, "sggNm": sgg}, key, "servList", sgg).assign(지역=f"{ctpv} {sgg}")
            for ctpv, sgg in [("서울특별시", "강남구"), ("강원특별자치도", "춘천시")]
        ],
        ignore_index=True,
    )
    local.to_parquet(PROCESSED_DIR / "res_welfare_local.parquet", index=False)
    write_meta("welfare_local", "복지로 지자체 복지서비스. 강남구·춘천시만 조회")

    print("■ 1365 봉사 일감")
    volunteer = pd.concat(
        [fetch_all("volunteer_1365", {"schSido": code}, key, "item", name).assign(시도=name) for code, name in SIDO.items()],
        ignore_index=True,
    )
    volunteer.to_parquet(PROCESSED_DIR / "res_volunteer.parquet", index=False)
    write_meta("volunteer_1365", "1365 자원봉사 모집 일감. 서울·강원 전체를 받아 시군구 코드로 대상 지역을 거른다")

    target = volunteer[volunteer["gugunCd"].isin(GUGUN)].copy()
    target["지역"] = target["gugunCd"].map(GUGUN)
    target.to_parquet(PROCESSED_DIR / "res_volunteer_target.parquet", index=False)
    print("\n■ 대상 지역 봉사 일감")
    print(target.groupby("지역").size().to_string())

    print(f"\n{'원본에서 다시 만듦' if from_raw else '수집 완료'} — 중앙부처 {len(central):,} · 지자체 {len(local):,} · 봉사 {len(volunteer):,}건")
    if not from_raw:
        print("원본 XML은 data/external/<슬러그>/raw/에 보관했습니다.")


if __name__ == "__main__":
    main()
