"""시설 표준데이터를 공공데이터포털 Open API로 전국 전체 받는다 (C3).

포털의 파일(CSV·XLS) 다운로드는 그리드 형식이라 5만 건에서 잘린다. 경로당 파일이
정확히 50,000행이었고, 포털 안내문도 "전체 데이터가 필요한 경우 API를 활용"하라고 한다.

수집 대상 (같은 인증키로 각 데이터 페이지에서 활용신청이 되어 있어야 한다)
  fac_senior_center : 전국마을회관및경로당표준데이터 (15114136)
  fac_library       : 전국도서관표준데이터           (15013109)
  ※ 전국사회복지시설표준데이터(15096296)는 좌표·주소를 주는 API가 없어 쓰지 않는다 (build_facility.py 참고)

인증키는 .env의 DATA_GO_KR_KEY에서 읽는다. Encoding·Decoding 어느 쪽 키를 넣어도 된다.
키 값은 로그에 출력하지 않는다.

원본 응답(JSON)은 data/external/<슬러그>/raw/에 페이지별로 그대로 보관하고,
합친 CSV를 data/external/<슬러그>/에 둔다. build_facility.py가 이 CSV를 읽는다.

실행: python scripts/fetch_facility_api.py [슬러그 ...]   (생략하면 전부)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import ROOT

EXTERNAL_DIR = ROOT / "data" / "external"
PAGE_SIZE = 1000
SLEEP = 0.2  # 호출 간격

SOURCES = {
    "fac_senior_center": {
        "name": "전국마을회관및경로당표준데이터",
        "url": "https://www.data.go.kr/data/15114136/standard.do",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_vill_hall_sen_cent_api",
    },
    "fac_library": {
        "name": "전국도서관표준데이터",
        "url": "https://www.data.go.kr/data/15013109/standard.do",
        "endpoint": "https://api.data.go.kr/openapi/tn_pubr_public_lbrry_api",
    },
}


def load_key() -> str:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATA_GO_KR_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return urllib.parse.unquote(key)  # Encoding 키도 원래 값으로 되돌린다
    raise SystemExit(".env의 DATA_GO_KR_KEY가 비어 있습니다.")


def call(endpoint: str, key: str, page: int) -> dict:
    query = urllib.parse.urlencode({"pageNo": page, "numOfRows": PAGE_SIZE, "type": "json"})
    url = f"{endpoint}?serviceKey={urllib.parse.quote(key, safe='')}&{query}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (401, 403) or "SERVICE_KEY" in body:
                raise SystemExit(f"인증 실패 ({e.code}). 이 데이터의 활용신청이 승인됐는지, 키를 정확히 넣었는지 확인하세요.\n{body[:300]}")
            err = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            err = repr(e)
        time.sleep(2 * (attempt + 1))
    raise SystemExit(f"{page}쪽 호출 실패: {err}")


def body_of(resp: dict) -> dict:
    resp = resp.get("response", resp)  # 표준데이터 API는 response 감싸개 없이 header·body를 바로 준다
    if "body" not in resp:
        raise SystemExit(f"예상과 다른 응답입니다: {json.dumps(resp, ensure_ascii=False)[:300]}")
    header = resp.get("header", {})
    if header.get("resultCode") not in ("00", "0", None):
        raise SystemExit(f"API 오류 {header.get('resultCode')}: {header.get('resultMsg')}")
    return resp["body"]


def fetch(slug: str, src: dict, key: str) -> pd.DataFrame:
    raw_dir = EXTERNAL_DIR / slug / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    first = call(src["endpoint"], key, 1)
    total = int(body_of(first)["totalCount"])
    pages = -(-total // PAGE_SIZE)
    print(f"[{slug}] 전국 {total:,}건, {pages}쪽")

    rows = []
    for page in range(1, pages + 1):
        resp = first if page == 1 else call(src["endpoint"], key, page)
        (raw_dir / f"page_{page:03d}.json").write_text(json.dumps(resp, ensure_ascii=False), encoding="utf-8")
        items = body_of(resp).get("items") or []
        rows.extend(items if isinstance(items, list) else items.get("item", []))
        if page % 10 == 0:
            print(f"  {page}/{pages}쪽, 누적 {len(rows):,}건")
        time.sleep(SLEEP)

    df = pd.DataFrame(rows)
    if len(df) != total:
        print(f"[경고] 받은 건수 {len(df):,} ≠ totalCount {total:,}")
    out = EXTERNAL_DIR / slug / f"{src['name']}_API_{date.today():%Y%m%d}.csv"
    for old in (EXTERNAL_DIR / slug).glob("*.csv"):  # 5만 건에서 잘린 파일 다운로드본은 치운다
        if old != out:
            old.rename(old.with_suffix(".csv.truncated"))
            print(f"  이전 파일을 옆으로 치웠습니다: {old.name} → {old.name}.truncated")
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"  저장: {out.relative_to(ROOT)} ({len(df):,}행, 열 {list(df.columns)})")
    write_meta(slug, src, total)
    return df


def write_meta(slug: str, src: dict, total: int) -> None:
    meta_path = EXTERNAL_DIR / slug / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    meta.update({
        "name": src["name"],
        "provider": "공공데이터포털 표준데이터 (각 지자체 제공)",
        "url": src["url"],
        "collected_at": date.today().isoformat(),
        "spatial_unit": "시설 좌표(WGS84)",
        "free": True,
        "note": f"Open API({src['endpoint']})로 전국 {total:,}건을 {PAGE_SIZE}건씩 받았다. 포털 파일 다운로드는 "
                "5만 건 상한에 잘려 쓰지 않는다. 페이지별 원본 응답은 raw/에, 합친 CSV는 이 폴더에 둔다.",
    })
    meta.setdefault("reference_date", "")
    meta.setdefault("license", "")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    key = load_key()
    targets = sys.argv[1:] or list(SOURCES)
    for slug in targets:
        fetch(slug, SOURCES[slug], key)


if __name__ == "__main__":
    main()
