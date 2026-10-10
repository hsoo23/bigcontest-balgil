import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'); plt.rcParams['font.family'] = fm.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc').get_name(); plt.rcParams['axes.unicode_minus'] = False
O, B, G = '#eb6834', '#2a78d6', '#9a9992'
d = pd.read_csv('out/features_segment.csv'); A = ['30대', '40대', '50대', '60대', '70대', '80대']
fig, ax = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
for a, c in zip(ax, ['춘천', '강남']):
    for sx, col in [('남성', B), ('여성', O)]:
        x = d[(d.city == c) & (d.sex == sx)].set_index('AGE').stay.reindex(A); a.plot(A, x.values, marker='o', color=col, lw=2, label=sx)
        a.annotate('%.1f%%' % x.iloc[-1], (5, x.iloc[-1]), textcoords='offset points', xytext=(6, 4 if sx == '남성' and c == '강남' else (-9 if c == '강남' else -3)), color=col, fontsize=9)
    a.set_title(c + ' — 머무는 곳에 쓰는 발길 비중(%)', fontsize=11, loc='left'); a.spines[['top', 'right']].set_visible(False); a.grid(axis='y', color='#eee'); a.set_ylim(0, 14); a.set_xlim(-.3, 5.8)
ax[0].legend(frameon=False); plt.tight_layout(); plt.savefig('fig/b1_stay.png', dpi=170); plt.close()
f = pd.read_csv('out/false_alarm.csv', index_col=0); n = pd.read_csv('out/nomed_false_alarm.csv', index_col=0)
fig, ax = plt.subplots(figsize=(7.5, 3)); lab = ['보정 없음', '계절 보정', '계절 + 함께 겪는 일 보정']; y = np.arange(3)
ax.barh(y + .2, f.iloc[:, 1], .36, color=G, label='필수에 병원·약국 포함'); ax.barh(y - .2, n.iloc[:, 1], .36, color=O, label='병원·약국 따로 떼면')
for i in range(3): ax.text(f.iloc[i, 1] + 1, i + .2, int(f.iloc[i, 1]), va='center', fontsize=9); ax.text(n.iloc[i, 1] + 1, i - .2, int(n.iloc[i, 1]), va='center', fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(lab); ax.invert_yaxis(); ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False, fontsize=9); ax.set_title('명절·공휴일 주간에 울린 알림 수 (12개 집단)', fontsize=11, loc='left'); plt.tight_layout(); plt.savefig('fig/b2_alarm.png', dpi=170); plt.close()
