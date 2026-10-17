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
import re
import subprocess
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
    그래서 로컬에 없는 파일은 지우지 않고 적혀 있던 줄을 그대로 옮긴다.

    옮긴 줄은 실행할 때 [유지]로 찍는다. 폴더에서 정말로 지운 파일도 이 규칙 때문에 남으므로,
    그때는 문서에서 그 줄을 손으로 지운다 — 자동으로 지우면 원본이 없는 PC에서 한 번 돌리는
    것만으로 기록이 날아간다."""
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


GIT_LIMIT_MB = 100  # GitHub가 막는 크기. 이보다 큰 원본은 meta.json만 올린다

# git에 없는 파일에 붙이는 꼬리표. 앞의 것은 옛 표기이고, 읽을 때 떼어 내 다시 붙인다
# (문구를 바꿀 때 이 목록에 옛 문구를 남겨 두면 한 번 돌려 전부 새 문구로 바뀐다).
TAILS = (
    " · **이 PC에 없음 — 기록만 유지**",              # 옛 표기 (환경에 딸려 있었다)
    " · **저장소에 없음 — 수집 방법은 위 note**",      # 옛 표기
    f" · **git 미포함 ({GIT_LIMIT_MB}MB 초과) — 해시로 대조**",
    " · **git 미포함 — 수집 방법은 위 note**",
)
BIG_TAIL, SMALL_TAIL = TAILS[-2], TAILS[-1]


def tracked() -> set[str] | None:
    """git이 들고 있는 data/external 파일 경로. 꼬리표의 기준을 **저장소 상태**로 둔다.

    로컬에 파일이 있느냐로 정하면 원본을 가진 PC와 없는 PC에서 돌릴 때마다 같은 여덟 줄이
    diff로 오간다(현수 #39 리뷰). git에 있느냐는 누가 돌려도 같은 답이라 그 오감이 멈춘다.
    아직 add하지 않은 파일은 「git 미포함」으로 나오는데 그 순간에는 사실이고, 커밋한 뒤
    다시 돌리면 꼬리표가 떨어진다. git을 쓸 수 없으면 None을 돌려 예전처럼 로컬 유무로 둔다."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", str(EXTERNAL_DIR.relative_to(ROOT))],
                             cwd=ROOT, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        print("[경고] git ls-files를 쓸 수 없어 꼬리표를 로컬 파일 유무로 정합니다")
        return None
    return {n for n in out.decode("utf-8").split(chr(0)) if n}


def _strip_tail(line: str) -> str:
    for t in TAILS:
        if line.endswith(t):
            return line[: -len(t)]
    return line


def _absent_tail(line: str) -> str:
    """git에 없는 파일의 꼬리표를 **적혀 있는 크기에서** 고른다. 「이 PC」는 제출물을 읽는
    사람에게 뜻이 없는 말이므로, 왜 없는지(100MB 초과인지)를 적는다."""
    m = re.search(r"—\s*([0-9.]+)\s*MB", line)
    big = m and float(m.group(1)) > GIT_LIMIT_MB
    return BIG_TAIL if big else SMALL_TAIL


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
    prev, in_git = recorded_files(), tracked()
    out += ["", "### 원본 파일", ""]
    for r in rows:
        out.append(f"**`{r['slug']}`**" + (f" — {r['meta'].get('note')}" if r["meta"].get("note") else ""))
        folder = EXTERNAL_DIR / r["slug"]
        lines, here = [], set()
        for path in r["files"]:
            name = path.relative_to(folder).as_posix()
            here.add(name)
            ln = f"- `{name}` — {path.stat().st_size / 1e6:.1f} MB, SHA-256 `{sha256(path)[:16]}…`"
            # 로컬에는 있지만 git에는 없는 원본(100MB 초과)도 같은 꼬리표를 받는다 — 그래야
            # 원본을 가진 PC와 없는 PC의 결과가 같아진다
            rel = path.relative_to(ROOT).as_posix()
            lines.append(ln if in_git is None or rel in in_git else ln + _absent_tail(ln))
        kept = [_strip_tail(ln) for ln in prev.get(r["slug"], []) if _name_of(ln) not in here]
        for ln in kept:
            lines.append(ln + _absent_tail(ln))
        if kept:
            print(f"[유지] {r['slug']}: 로컬에 없어 기록만 옮긴 파일 {len(kept)}개 — "
                  + ", ".join(_name_of(ln) for ln in kept))
        if not lines:
            out.append("- (원본 파일 없음)")
        # 파일 이름으로 정렬한다. 로컬에 있는 파일을 먼저 넣고 기록에서 옮긴 줄을 뒤에 붙이면,
        # 원본이 일부만 있는 PC마다 블록 안 순서가 달라져 diff 가 오간다(수경 #55 리뷰)
        out += sorted(lines, key=_name_of)
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
