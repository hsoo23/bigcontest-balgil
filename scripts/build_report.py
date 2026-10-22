"""보고서 열한 절을 제출본 한 벌로 묶는다 (E1 통합 편집) → reports/발길_분석보고서.md.

**왜 스크립트인가.** `docs/draft/*.md`는 **작업용 파일**이다 — 머리줄에 「담당 수경 · 10/21까지」가,
끝에 「남은 일」·「채우기 전 확인」이 붙어 있다. 셋이 서로 보라고 적은 메모이고 심사위원에게
보낼 글이 아니다. 손으로 지우면 작업 메모가 사라져 다음 수정이 어려워지고, 제출 전에 다시
지웠는지 세어 봐야 한다. 그래서 **원본은 그대로 두고 묶을 때 걷어낸다.**

걷어내는 것 넷 — 왜 그것인지 같이 적는다.
  담당·기한 머리줄   「담당 윤지 · 10/20까지」. 지난 날짜가 제출본에 남으면 늦은 것처럼 읽힌다
  남은 일 · 채우기 전 확인 꼬리글   우리끼리의 할 일이다
  깃허브 이슈 링크   저장소가 private 이라 심사위원이 누르면 404 다. **번호는 남긴다** —
                    「#88에서 정했습니다」는 판단의 이력이고, 재현 코드 zip 안에서 찾을 수 있다
  절 사이의 `---` 겹침   절을 이으면 가로줄이 두 번 그려진다

안 건드리는 것 — **본문 한 글자도 바꾸지 않는다.** 숫자·문장·표는 그대로다. 이 스크립트가
글을 고치기 시작하면 「보고서에서 본 문장」과 「저장소의 문장」이 갈려서, 교차 검토가 소용없어진다.

확인도 같이 한다(끝에 요약을 찍는다).
  `〈 〉` 자리   하나라도 남으면 치환이 덜 끝난 것이다
  깃허브 URL    걷어낸 뒤에도 남아 있으면 꼴이 다른 링크다
  절 순서·개수  열한 절(00은 발표자료라 뺀다)

입력: docs/draft/01_문제.md … 10_한계.md (저장소에 있는 그대로)
출력: reports/발길_분석보고서.md  (PDF 는 이 파일로 만든다 — 제출물 이름은 발길_분석보고서.pdf)
실행: python scripts/build_report.py [--check]   (--check 는 쓰지 않고 확인만 한다)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs" / "draft"
OUT = ROOT / "reports" / "발길_분석보고서.md"

SECTIONS = ["01_문제", "02_지표", "03_데이터", "04_분석근거", "05_모델링", "06_터전",
            "07_에이전트", "08_시나리오화면", "09_영향력실현가능성", "10_한계"]

# 부록 셋 — 보고서_목차 2절의 「부록 A · B · C」. 본문이 「수치표」·「외부 데이터 목록」을
# 계속 가리키므로, 같이 묶어야 심사위원이 그 자리에서 확인할 수 있다
APPENDIX = [("부록 A", "최종 수치표 — 모든 숫자의 단일 출처", ROOT / "docs" / "최종수치표.md", None),
            ("부록 B", "데이터 출처 · 외부 데이터 목록", ROOT / "docs" / "external_data.md", None),
            ("부록 C", "문서 간 불일치 처리", ROOT / "docs" / "실행계획.md", "## 부록 — 문서 간 불일치 처리")]

HEAD = re.compile(r"^\*\*(?:담당|윤지 · 초안)[^*]*\*\*")        # 「**담당 수경 · 10/21까지 …**」
TAIL = re.compile(r"^\*\*(?:남은 일|채우기 전 확인)\*\*")       # 절 끝의 우리끼리 메모
ISSUE = re.compile(r"\[(#\d+)\]\(https://github\.com/[^)]*\)")  # [#88](url) → #88
URL = re.compile(r"https://github\.com/\S+")
# 채울 자리는 `〈수치표: 이름〉`과 빈 `〈 〉`뿐이다(draft/README 2번). `〈양〉`·`〈연속성〉`처럼
# 홑화살괄호를 쓰는 것이 또 있다 — 에이전트 브리핑의 **출력 라벨**이라 본문에 그대로 실린다
SLOT = re.compile(r"〈\s*(?:수치표\s*:[^〉]*)?\s*〉")

COVER = """# 발길 — 고립은 발길이 좁아지고 끊기는 일이다

**제14회 빅콘테스트 · AI데이터 활용 분야 · 팀 또커톤**

사회적 고립 예방 및 대응을 위한 AI 에이전트 — 분석보고서

> **본 제출물은 발표자료이고 이 보고서는 기타자료(상세판)입니다.** 같은 절 번호를 씁니다.
>
> 이 보고서의 모든 수치는 `docs/최종수치표.md` 한 곳에서 나옵니다. 재현 방법은 절마다
> 「재현」 줄에 적었고, 코드는 제출한 재현 코드에 들어 있습니다. `#숫자`는 저장소 이슈 번호로,
> 그 판단을 어디서 정했는지 가리킵니다.
"""


def strip_section(text: str) -> tuple[str, dict[str, int]]:
    """작업용 표시를 걷어낸다. 본문은 바꾸지 않는다."""
    n = {"머리줄": 0, "꼬리글": 0, "이슈 링크": 0}
    lines, out, drop_tail = text.splitlines(), [], False
    for i, ln in enumerate(lines):
        if HEAD.match(ln):
            n["머리줄"] += 1
            continue
        if TAIL.match(ln):
            n["꼬리글"] += 1
            drop_tail = True
            # 꼬리글 바로 앞의 가로줄과 빈 줄도 같이 걷는다
            while out and out[-1].strip() in ("", "---"):
                out.pop()
            continue
        if drop_tail and ln.strip() == "":
            continue
        drop_tail = False
        out.append(ln)
    body = "\n".join(out)
    body, k = ISSUE.subn(r"\1", body)
    n["이슈 링크"] = k
    return body.strip("\n"), n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="쓰지 않고 확인만 한다")
    a = ap.parse_args()

    parts, total, warn = [COVER], {"머리줄": 0, "꼬리글": 0, "이슈 링크": 0}, []
    toc = []
    for name in SECTIONS:
        p = DRAFT / f"{name}.md"
        if not p.exists():
            warn.append(f"없는 절: {p.name}")
            continue
        body, n = strip_section(p.read_text(encoding="utf-8"))
        for k in total:
            total[k] += n[k]
        head = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), name)
        toc.append(head)
        for slot in SLOT.findall(body):
            warn.append(f"{p.name}: 채우지 않은 자리 {slot}")
        for url in URL.findall(body):
            warn.append(f"{p.name}: 남은 링크 {url}")
        parts.append(body)

    for label, title, src, start in APPENDIX:
        if not src.exists():
            warn.append(f"없는 부록: {src.name}")
            continue
        raw = src.read_text(encoding="utf-8")
        if start:                                    # 실행계획은 부록 소절만 떼어 온다
            if start not in raw:
                warn.append(f"{src.name}: 「{start}」를 찾지 못했습니다")
                continue
            raw = "# " + raw[raw.index(start):].lstrip("# ")
        body, n = strip_section(raw)
        for k in total:
            total[k] += n[k]
        body = re.sub(r"^# (?:부록\s*—\s*)?", f"# {label}. ", body, count=1)
        toc.append(next(l[2:].strip() for l in body.splitlines() if l.startswith("# ")))
        for url in URL.findall(body):
            warn.append(f"{src.name}: 남은 링크 {url}")
        parts.append(body)

    items = [f"- {t}" for t in toc]       # 절 제목에 이미 번호가 있다
    doc = COVER + "\n## 목차\n\n" + "\n".join(items) + "\n\n---\n\n"
    doc += "\n\n---\n\n".join(parts[1:]) + "\n"

    if not a.check:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(doc, encoding="utf-8")
        print(f"저장: {OUT.relative_to(ROOT)}  —  {len(SECTIONS)}절 · {len(doc.splitlines()):,}줄 · {len(doc):,}자")
    else:
        print(f"확인만 했습니다 — {len(SECTIONS)}절 · {len(doc.splitlines()):,}줄")
    print("걷어낸 것: " + " · ".join(f"{k} {v}" for k, v in total.items()))
    if warn:
        print("확인할 것:")
        for w in warn:
            print("  " + w)
    else:
        print("확인할 것 없음 — 빈 자리 0개 · 남은 링크 0개")


if __name__ == "__main__":
    main()
