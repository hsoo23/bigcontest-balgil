"""docs/의 문서를 노션 복붙용으로 변환한다 → docs/notion/

노션은 마크다운 붙여넣기에서 표·제목·굵게·인용·코드블록을 그대로 변환하지만
상대 링크(`기획안_발길.md`)는 깨진다. 레포 경로 참조도 레포가 없는 팀원에게는
의미가 없다. 그래서 바꾸는 것은 네 가지뿐이다.

  1 상대 .md 링크 → 굵은 글씨
  2 문서 간 상호 참조 → 노션 문서 이름
  3 레포 경로 안내 블록 → 세트 안내 문장
  4 제목을 팀원이 읽을 이름으로 교체하고 한 줄 설명을 붙인다

본문과 수치는 손대지 않는다. docs/가 원본이고 docs/notion/은 파생물이므로
원본을 고친 뒤 이 스크립트를 다시 돌리면 된다.

실행: python scripts/make_notion.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "docs"
OUT_DIR = ROOT / "docs" / "notion"

# 파일명 → (노션 문서 제목, 한 줄 설명)
DOCS = {
    "기획안_발길.md": (
        "발길 — 기획안",
        "고립을 「발길이 좁아지고 끊기는 일」로 정의한 출품 기획안입니다. 발길을 양·질·연속성·터전 네 면으로 재고, 그 한 개념에서 탐지·판단·원인 분석·자원 연결을 모두 도출합니다.",
    ),
    "분석결과.md": (
        "발길 — 분석 결과",
        "네 지표가 실제로 성립하는지 데이터로 검증한 기록입니다. 대회 제출물 중 「데이터 분석 근거 자료」의 초안을 겸합니다.",
    ),
    "협업규칙.md": (
        "발길 — 협업 규칙",
        "브랜치·커밋·수치 출처·작업 메모 규칙입니다. 10/10 회의에서 확정합니다.",
    ),
    "실행계획.md": (
        "발길 — 추진 계획",
        "팀원 「안심 신호등 × 단골 안부 통합 최종본」을 흡수해 다섯 트랙으로 나눈 실행 계획입니다. 분업을 정하기 위한 문서입니다.",
    ),
    "제출요건.md": (
        "발길 — 제출 요건",
        "공식 페이지에서 확인한 마감·제출 방법·제출물 형태입니다. 마감은 10/26(월)이고 본 제출물은 발표자료입니다.",
    ),
    "보고서_목차.md": (
        "발길 — 제출물 목차와 서식",
        "발표자료 15장과 보고서 10절의 목차, 그리고 셋이 따로 써도 한 사람이 쓴 것처럼 맞춰지는 공통 서식입니다.",
    ),
    "설계자료_요구항목.md": (
        "발길 — 설계자료 2종 요구 항목",
        "규정상 함께 내는 가상 데이터 생성 설계자료(E5)와 LLM 활용 설계자료(E6)에 무엇을 적어야 하는지 항목으로 정리했습니다.",
    ),
}

SET_NOTE = (
    "> **문서 세 개가 한 세트입니다.** "
    "「발길 — 기획안」은 무엇을 만드는가, 「발길 — 분석 결과」는 그 근거, "
    "「발길 — 추진 계획」은 누가 언제 무엇을 하는가입니다. "
    "여기에 「발길 — 제출 요건」(마감과 규정), 「발길 — 제출물 목차와 서식」(무엇을 어떻게 쓰는가), "
    "「발길 — 설계자료 2종 요구 항목」(규정상 함께 내는 것)이 붙습니다."
)

# 레포 경로 참조 → 노션 문서 이름
PATH_TO_TITLE = {
    "docs/기획안_발길.md": "「발길 — 기획안」",
    "docs/분석결과.md": "「발길 — 분석 결과」",
    "docs/실행계획.md": "「발길 — 추진 계획」",
    "docs/협업규칙.md": "「발길 — 협업 규칙」",
    "협업규칙.md": "「발길 — 협업 규칙」",
    "기획안_발길.md": "「발길 — 기획안」",
    "분석결과.md": "「발길 — 분석 결과」",
    "실행계획.md": "「발길 — 추진 계획」",
    "docs/제출요건.md": "「발길 — 제출 요건」",
    "docs/보고서_목차.md": "「발길 — 제출물 목차와 서식」",
    "docs/설계자료_요구항목.md": "「발길 — 설계자료 2종 요구 항목」",
    "제출요건.md": "「발길 — 제출 요건」",
    "보고서_목차.md": "「발길 — 제출물 목차와 서식」",
    "설계자료_요구항목.md": "「발길 — 설계자료 2종 요구 항목」",
}


def convert(text: str, title: str, lead: str) -> str:
    # 1. 상대 .md 링크 → 굵은 글씨 (http 링크는 노션에서 작동하므로 그대로 둔다)
    text = re.sub(
        r"\[([^\]]+)\]\((?!https?://)[^)]*\.md\)",
        lambda m: f"**{m.group(1)}**",
        text,
    )

    # 2. 백틱으로 감싼 레포 경로 참조 → 노션 문서 이름
    for path, name in PATH_TO_TITLE.items():
        text = text.replace(f"`{path}`", name)
        text = text.replace(f"**`{path}`**", name)

    # 3. 원본의 '관련 문서' 안내 블록을 세트 안내로 교체
    text = re.sub(
        r"\n관련 문서\n(?:- .*\n)+",
        "\n",
        text,
    )

    # 4. 첫 H1을 팀원용 제목으로 교체하고 설명·세트 안내를 머리에 둔다
    body = re.sub(r"\A# [^\n]*\n", "", text, count=1).lstrip("\n")
    out = f"# {title}\n\n{lead}\n\n{SET_NOTE}\n\n---\n\n{body}"

    return re.sub(r"\n{3,}", "\n\n", out)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, (title, lead) in DOCS.items():
        src = SRC_DIR / name
        if not src.exists():
            print(f"  건너뜀 — {src} 없음")
            continue
        out = convert(src.read_text(encoding="utf-8"), title, lead)
        # newline="\n": 윈도우 텍스트 모드가 CRLF로 쓰면 OS가 다른 사람이
        # 다시 만들 때마다 파일 전체가 바뀐 것으로 잡힌다. 원본과 같은 LF로 고정한다.
        (OUT_DIR / name).write_text(out, encoding="utf-8", newline="\n")
        print(f"  {OUT_DIR.relative_to(ROOT)}/{name}  {len(out):,}자")

    leftovers = [
        f"{p.name}:{i}"
        for p in OUT_DIR.glob("*.md")
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\]\((?!https?://)[^)]*\.md\)", line)
    ]
    print(f"\n남은 상대 링크: {', '.join(leftovers) if leftovers else '없음'}")
    print("\n붙여넣기: pbcopy < docs/notion/<파일명>")
    print("긴 문서는 '---' 기준으로 2~3번 나눠 붙이면 표 변환이 안정적입니다.")


if __name__ == "__main__":
    main()
