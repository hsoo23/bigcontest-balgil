"""외부 공공데이터의 출처와 원본 파일을 기록·검증한다.

대회 규정상 외부 데이터는 출처와 수집 방법을 명시하고 원본 파일을 제출해야 한다.
원본은 `data/external/<슬러그>/`에 가공 없이 보관하고, 같은 폴더의 `meta.json`에
출처를 기록한다. 이 스크립트가 그 기록을 모아 `docs/external_data.md`를 갱신한다.

사용법
  python scripts/register_external.py --init <슬러그>   meta.json 템플릿 생성
  python scripts/register_external.py                   목록 문서 갱신
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balgil.data import ROOT

EXTERNAL_DIR = ROOT / "data" / "external"
DOC = ROOT / "docs" / "external_data.md"
BEGIN, END = "<!-- BEGIN: 자동 생성 -->", "<!-- END: 자동 생성 -->"

TEMPLATE = {
    "name": "",  # 데이터셋 정식 명칭
    "provider": "",  # 제공 기관
    "url": "",  # 내려받은 페이지 URL
    "collected_at": "",  # 수집일 (YYYY-MM-DD)
    "reference_date": "",  # 데이터 기준 시점 (예: 2026-08-31)
    "spatial_unit": "",  # 공간 단위 (행정동/시군구/좌표 등)
    "license": "",  # 이용허락 범위 (예: 이용허락범위 제한 없음)
    "free": True,  # 무료 여부. 유료 데이터는 사용 시 수상 취소
    "note": "",  # 수집 방법 등 비고
}
REQUIRED = ["name", "provider", "url", "collected_at", "license"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def init(slug: str) -> None:
    folder = EXTERNAL_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    meta = folder / "meta.json"
    if meta.exists():
        raise SystemExit(f"이미 존재합니다: {meta.relative_to(ROOT)}")
    template = dict(TEMPLATE, collected_at=date.today().isoformat())
    meta.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"생성했습니다: {meta.relative_to(ROOT)}\n원본 파일을 {folder.relative_to(ROOT)}/ 에 두고 meta.json을 채우세요.")


def collect() -> list[dict]:
    rows = []
    for meta_path in sorted(EXTERNAL_DIR.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        missing = [k for k in REQUIRED if not meta.get(k)]
        if missing:
            print(f"[경고] {meta_path.relative_to(ROOT)}: 누락된 항목 {', '.join(missing)}")
        if meta.get("free") is False:
            print(f"[경고] {meta_path.relative_to(ROOT)}: 유료 데이터로 표시되어 있습니다. 사용 시 수상이 취소됩니다.")
        folder = meta_path.parent
        files = sorted(
            (p for p in folder.rglob("*") if p.is_file() and p.name != "meta.json"),
            key=lambda p: p.relative_to(folder).as_posix(),
        )
        rows.append({"slug": meta_path.parent.name, "meta": meta, "files": files})
    return rows


def recorded_files() -> dict[str, list[str]]:
    """이미 문서에 적혀 있는 원본 파일 줄을 슬러그별로 읽어 둔다.

    100MB가 넘어 git에 올리지 못한 원본(sbiz_store 상가 서울 302MB, sgis_boundary 경계 135MB)은
    받은 사람의 PC에만 있다. 그 PC가 아닌 곳에서 이 스크립트를 돌리면 폴더에 파일이 없으므로
    줄이 사라지고, **제출할 수 없는 파일의 유일한 증거인 SHA-256이 같이 지워진다.**
    그래서 로컬에 없는 파일은 지우지 않고 적혀 있던 줄을 그대로 옮긴다."""
    if not DOC.exists():
        return {}
    text = DOC.read_text(encoding="utf-8")
    if BEGIN not in text:
        return {}
    body = text.partition(BEGIN)[2].partition(END)[0]
    out: dict[str, list[str]] = {}
    slug = None
    for line in body.splitlines():
        if line.startswith("**`") and line[3:].partition("`")[0]:
            slug = line[3:].partition("`")[0]
            out.setdefault(slug, [])
        elif slug and line.startswith("- `"):
            out[slug].append(line)
    return out


def _name_of(line: str) -> str:
    return line[3:].partition("`")[0]


def render(rows: list[dict]) -> str:
    if not rows:
        return "아직 등록된 외부 데이터가 없습니다. `python scripts/register_external.py --init <슬러그>`로 시작하세요."
    out = ["| 슬러그 | 데이터셋 | 제공처 | 기준 시점 | 공간 단위 | 수집일 | 라이선스 | 출처 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        m = r["meta"]
        url = f"[링크]({m['url']})" if m.get("url") else ""
        out.append(
            f"| `{r['slug']}` | {m.get('name','')} | {m.get('provider','')} | {m.get('reference_date','')} "
            f"| {m.get('spatial_unit','')} | {m.get('collected_at','')} | {m.get('license','')} | {url} |"
        )
    prev = recorded_files()
    out += ["", "### 원본 파일", ""]
    for r in rows:
        out.append(f"**`{r['slug']}`**" + (f" — {r['meta'].get('note')}" if r["meta"].get("note") else ""))
        folder = EXTERNAL_DIR / r["slug"]
        lines, here = [], set()
        for path in r["files"]:
            name = path.relative_to(folder).as_posix()
            here.add(name)
            lines.append(f"- `{name}` — {path.stat().st_size / 1e6:.1f} MB, SHA-256 `{sha256(path)[:16]}…`")
        kept = [ln for ln in prev.get(r["slug"], []) if _name_of(ln) not in here]
        for ln in kept:
            suffix = " · **이 PC에 없음 — 기록만 유지**"
            out_line = ln if ln.endswith(suffix) else ln + suffix
            lines.append(out_line)
        if not lines:
            out.append("- (원본 파일 없음)")
        out += lines
        out.append("")
    return "\n".join(out)


def update_doc(body: str) -> None:
    header = f"""# 외부 공공데이터 목록

대회 규정상 외부 데이터는 무료·공개 데이터만 사용할 수 있고(유료 데이터 사용 시 수상 취소),
출처와 수집 방법을 명시하고 활용한 원본 파일을 함께 제출해야 합니다.

- 원본 파일은 가공 없이 `data/external/<슬러그>/`에 보관합니다. (`data/`는 git에 올리지 않습니다)
- 출처는 같은 폴더의 `meta.json`에 기록합니다. `python scripts/register_external.py --init <슬러그>`로 템플릿을 만듭니다.
- 아래 표는 `python scripts/register_external.py` 실행 시 자동으로 갱신됩니다.

{BEGIN}
{{body}}
{END}
"""
    DOC.parent.mkdir(parents=True, exist_ok=True)
    if DOC.exists() and BEGIN in DOC.read_text(encoding="utf-8"):
        text = DOC.read_text(encoding="utf-8")
        head, _, rest = text.partition(BEGIN)
        _, _, tail = rest.partition(END)
        DOC.write_text(f"{head}{BEGIN}\n{body}\n{END}{tail}", encoding="utf-8")
    else:
        DOC.write_text(header.format(body=body), encoding="utf-8")
    print(f"갱신했습니다: {DOC.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", metavar="슬러그", help="새 외부 데이터 폴더와 meta.json 템플릿 생성")
    args = parser.parse_args()

    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    if args.init:
        init(args.init)
        return
    update_doc(render(collect()))


if __name__ == "__main__":
    main()
