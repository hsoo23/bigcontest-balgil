"""지역 일반화 — 한 도시에서 배운 좁아짐 분류기가 다른 도시에서도 서는가 (B1, 타당성 검증 ②)

기획안 7절 「발길 지수 — 합성 + 타당성 검증」의 네 항목 중 '지역 일반화'다.
강남에서만 학습해 춘천에 적용하고, 반대로도 한다. 두 도시는 밀도·연령 구성·
자원 분포가 달라서, 순위가 무너지지 않으면 임계값을 지역마다 다시 잡는 것으로
운영할 수 있다는 근거가 된다.

b3_models.py가 이미 '칸 통째로 빼기'를 하지만 그것은 같은 도시의 다른 칸이
학습에 남는다. 도시를 통째로 빼야 "다른 동네에서도 서는가"에 답한다.

입력: data/processed/reanalysis/weekly_panel.csv (b3_models.py가 만든다)
출력: data/processed/reanalysis/city_transfer.csv

실행: python scripts/explore_city_transfer.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from balgil.data import PROCESSED_DIR

OUT = PROCESSED_DIR / "reanalysis"
F = ["breadth_z", "stay_z", "narrow", "d_narrow", "d_stay_z", "d_breadth_z",
     "m3", "meal", "anon", "med", "evening"]


def _models():
    return {
        "로지스틱": make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000)),
        "랜덤포레스트": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced", random_state=0),
    }


def main() -> None:
    P = pd.read_csv(OUT / "weekly_panel.csv")
    D = P.dropna(subset=["y"]).copy()
    D["y"] = D.y.astype(int)
    D["city"] = D.seg.str.split().str[0]
    print(f"표본 {len(D)} | 칸 {D.seg.nunique()} | 도시 {sorted(D.city.unique())}")

    rows = []
    for train, test in [("강남", "춘천"), ("춘천", "강남")]:
        tr, te = D[D.city == train], D[D.city == test]
        base = te.top.values.astype(float)          # 기준선: 이번 주 그대로
        rows.append(dict(학습=train, 적용=test, 모델="기준선(이번 주 그대로)",
                         AUC=roc_auc_score(te.y, base), 표본=len(te),
                         양성=int(te.y.sum()), 새진입=int(((te.top == 0) & (te.y == 1)).sum()),
                         새진입_잡음=0))
        for name, m in _models().items():
            p = m.fit(tr[F], tr.y).predict_proba(te[F])[:, 1]
            new = (te.top == 0).values
            rows.append(dict(학습=train, 적용=test, 모델=name,
                             AUC=roc_auc_score(te.y, p), 표본=len(te),
                             양성=int(te.y.sum()), 새진입=int((new & (te.y == 1)).sum()),
                             새진입_잡음=int((new & (te.y == 1) & (p >= .5)).sum())))

    # 같은 도시 안에서 배운 경우 (비교 기준)
    for city in ["강남", "춘천"]:
        d = D[D.city == city]
        tr, te = d[d.w <= 20], d[d.w > 20]
        for name, m in _models().items():
            p = m.fit(tr[F], tr.y).predict_proba(te[F])[:, 1]
            new = (te.top == 0).values
            rows.append(dict(학습=f"{city}(앞 21주)", 적용=f"{city}(뒤 4주)", 모델=name,
                             AUC=roc_auc_score(te.y, p), 표본=len(te),
                             양성=int(te.y.sum()), 새진입=int((new & (te.y == 1)).sum()),
                             새진입_잡음=int((new & (te.y == 1) & (p >= .5)).sum())))

    R = pd.DataFrame(rows).round(3)
    print("\n" + R.to_string(index=False))
    R.to_csv(OUT / "city_transfer.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {(OUT / 'city_transfer.csv').name}")


if __name__ == "__main__":
    main()
