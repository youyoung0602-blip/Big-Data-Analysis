from pathlib import Path
import argparse, hashlib, json, re, platform
from collections import Counter
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--local', type=Path, required=True)
args = parser.parse_args()
out = args.repo / '09_수정검색_발표자료'
out.mkdir(exist_ok=True)
tables = out / '03_집계표'
figures = out / '04_그래프'
tables.mkdir(exist_ok=True)
figures.mkdir(exist_ok=True)
args.local.mkdir(exist_ok=True)
d = pd.read_csv(args.source).fillna('')
assert d['Lens ID'].is_unique

# Membership intersections connect records even when member lists differ in order or coverage.
parent = list(range(len(d)))
def root(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
seen = {}
for i, row in d.iterrows():
    members = set(str(row['Simple Family Members']).split(';;')) | {row['Lens ID']}
    for member in members - {''}:
        if member in seen:
            parent[root(i)] = root(seen[member])
        else:
            seen[member] = i
d['family_group'] = [root(i) for i in range(len(d))]
d['pub_year'] = pd.to_numeric(d['Publication Year'], errors='coerce')
d['priority'] = pd.to_datetime(d['Earliest Priority Date'], errors='coerce')
window = d[d.pub_year.between(2015, 2024)].copy()
# Choose an actual in-window document with complete text, earliest publication, stable ID tie break.
reps = window.sort_values(['Publication Date', 'Lens ID']).drop_duplicates('family_group').copy()
group_priority = d.groupby('family_group').priority.min()
reps['family_priority'] = reps.family_group.map(group_priority)
reps['priority_year'] = reps.family_priority.dt.year
cpc_union = d.groupby('family_group')['CPC Classifications'].agg(lambda s: ';;'.join(sorted(set(';;'.join(s).split(';;')) - {''})))
reps['family_cpc'] = reps.family_group.map(cpc_union)
reps.to_csv(args.local / 'family_representatives_LOCAL_ONLY.csv', index=False, encoding='utf-8-sig')

old = args.repo / '08_검색식개선_단계별/02_용어정제_TFIDF'
stop = set(pd.read_csv(old / 'stopwords.csv').term)
plural = dict(pd.read_csv(old / 'plural_mapping.csv').itertuples(index=False, name=None))
rules = [
    (r'\buser equipments?(?:\s*\(\s*ues?\s*\))?|\bues?\b', 'user_equipment'),
    (r'\bbase stations?\b', 'base_station'),
    (r'\bchannel state information(?:\s*\(\s*csi\s*\))?|\bcsi\b', 'channel_state_information'),
    (r'\bdiscontinuous reception(?:\s*\(\s*drx\s*\))?|\bdrx\b', 'drx'),
    (r'\bhybrid automatic repeat request(?:\s*\(\s*harq\s*\))?|\bharq\b', 'harq'),
    (r'\bnew radio(?:\s*\(\s*nr\s*\))?|\bnr\b', 'nr'),
    (r'\blong[ -]term evolution(?:\s*\(\s*lte\s*\))?|\blte\b', 'lte'),
    (r'\bwi[ -]?fi\b', 'wifi'),
    (r'\bside[ -]?links?\b', 'sidelink'),
    (r'\breference signals?\b', 'reference_signal'),
    (r'\bresource pools?\b', 'resource_pool'),
    (r'\brandom access\b', 'random_access'),
    (r'\bmachine learning\b', 'machine_learning'),
    (r'\bneural networks?\b', 'neural_network'),
]
def clean(text):
    text = text.lower()
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)
    tokens = [plural.get(t, t) for t in re.findall(r'\b[a-z0-9][a-z0-9_]+\b', text)]
    return ' '.join(t for t in tokens if not t.isdigit() and t not in stop)

# Separate fields prevent a bigram joining the final title word to the first abstract word.
titles = reps.Title.map(clean)
abstracts = reps.Abstract.map(clean)
def analyze(text):
    title, abstract = text.split('\n', 1)
    features = []
    for field in (title, abstract):
        words = field.split()
        features.extend(words)
        features.extend(a + ' ' + b for a, b in zip(words, words[1:]))
    return features
texts = titles + '\n' + abstracts
sens = []
for threshold in (3, 5, 10):
    v = TfidfVectorizer(analyzer=analyze, min_df=threshold, max_df=1.0, sublinear_tf=True, norm='l2', smooth_idf=True)
    matrix = v.fit_transform(texts)
    terms = v.get_feature_names_out()
    means = np.asarray(matrix.mean(axis=0)).ravel()
    order = np.argsort(-means)
    sens.append({'min_df': threshold, 'features': matrix.shape[1], 'empty_documents': int((matrix.getnnz(axis=1) == 0).sum()), 'top20': terms[order[:20]].tolist()})
    if threshold == 5:
        X = matrix
        vocabulary = terms
        rank = pd.DataFrame({'term': terms, 'mean_tfidf': means, 'document_frequency': np.asarray((matrix > 0).sum(axis=0)).ravel()}).sort_values(['mean_tfidf', 'term'], ascending=[False, True])
        rank.to_csv(tables / 'tfidf_keywords.csv', index=False, encoding='utf-8-sig')
        from scipy.sparse import save_npz
        save_npz(args.local / 'tfidf.npz', X)
        (args.local / 'vocabulary.json').write_text(json.dumps(terms.tolist()), encoding='utf-8')
baseline_top = set(sens[1]['top20'])
for item in sens:
    item['top20_overlap_with_df5'] = len(set(item['top20']) & baseline_top) / 20
(tables / 'tfidf_sensitivity.json').write_text(json.dumps(sens, ensure_ascii=False, indent=2), encoding='utf-8')
assert np.isfinite(X.data).all() and (X.data >= 0).all()
assert np.allclose(np.sqrt(X.multiply(X).sum(axis=1)).A1, 1)

publication = d.groupby('pub_year').size().rename('records').to_frame()
publication['in_2015_2024'] = publication.index.to_series().between(2015, 2024)
publication.to_csv(tables / 'publication_year_counts.csv', encoding='utf-8-sig')
priority = reps.priority_year.value_counts().sort_index().rename('families').to_frame()
priority.to_csv(tables / 'priority_year_counts.csv', encoding='utf-8-sig')
periods = ['2015–2019', '2020–2024']
reps['period'] = pd.cut(reps.priority_year, [2014, 2019, 2024], labels=periods)
denom = reps.period.value_counts().reindex(periods, fill_value=0)
cpc_rows = []
for period in periods:
    counts = Counter()
    for value in reps.loc[reps.period == period, 'family_cpc']:
        codes = set(re.findall(r'\bH04W(\d+)/', value))
        for code in codes:
            counts['H04W' + code + '/00'] += 1
    for code, count in counts.items():
        cpc_rows.append({'period': period, 'cpc': code, 'families': count, 'denominator': int(denom[period]), 'share_percent': 100 * count / denom[period]})
cpc = pd.DataFrame(cpc_rows)
cpc.to_csv(tables / 'cpc_period_counts.csv', index=False, encoding='utf-8-sig')
allcpc = Counter(code for value in reps.family_cpc for code in set(re.findall(r'\bH04W(\d+)/', value)))
topcodes = ['H04W' + x + '/00' for x, _ in allcpc.most_common(10)]

def hits(pattern):
    return int((reps.Title + ' ' + reps.Abstract).str.contains(pattern, case=False, regex=True).sum())
lexical = {
    'sidelink_or_pc5': hits(r'\bsidelinks?\b|\bside[ -]links?\b|\bpc5\b'),
    'drx': hits(r'\bdrx\b|\bdiscontinuous reception\b'),
    'relay': hits(r'\brelay\w*\b'),
}
lexical_patterns = {
    'sidelink_pc5': r'\bsidelinks?\b|\bside[ -]links?\b|\bpc5\b',
    'drx': r'\bdrx\b|\bdiscontinuous reception\b',
    'relay': r'\brelay\w*\b',
}
lexical_rows = []
for label, pattern in lexical_patterns.items():
    mask = (reps.Title + ' ' + reps.Abstract).str.contains(pattern, case=False, regex=True)
    for period in periods:
        count = int((mask & (reps.period == period)).sum())
        lexical_rows.append({'term_group': label, 'period': period, 'families': count, 'denominator': int(denom[period]), 'share_percent': 100 * count / denom[period]})
pd.DataFrame(lexical_rows).to_csv(tables / 'lexical_period_counts.csv', index=False, encoding='utf-8-sig')
anchor = (reps.Title + ' ' + reps.Abstract).str.contains(lexical_patterns['sidelink_pc5'], case=False, regex=True)
details = (reps.Title + ' ' + reps.Abstract).str.contains(r'\bresource\w*\b|\bschedul\w*\b|\bgrant\w*\b|\bpreempt\w*\b|\bdrx\b|\bdiscontinuous reception\b|\brelay\w*\b', case=False, regex=True)
lexical['sidelink_and_resource_drx_relay'] = int((anchor & details).sum())
stats = {
    'source_file': args.source.name, 'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
    'records_all': len(d), 'records_2015_2024': len(window), 'records_outside_window': len(d) - len(window),
    'families_all_connected_members': d.family_group.nunique(), 'families_2015_2024': len(reps),
    'duplicate_family_records_in_window': len(window) - len(reps),
    'missing_title': int((d.Title == '').sum()), 'missing_abstract': int((d.Abstract == '').sum()),
    'missing_priority_records': int(d.priority.isna().sum()), 'missing_priority_families_in_window': int(reps.family_priority.isna().sum()),
    'period_denominators': {k: int(v) for k, v in denom.items()},
    'outside_priority_periods': int(reps.period.isna().sum()),
    'lexical_family_counts': lexical, 'tfidf_shape': list(X.shape), 'tfidf_empty_documents': 0,
    'python': platform.python_version(), 'sklearn': sklearn.__version__,
    'analysis_date': '2026-11-18', 'source_query_available': False,
}
(tables / 'data_audit.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2, default=int), encoding='utf-8')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11})
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
colors = ['#087F8C' if 2015 <= year <= 2024 else '#F2B650' for year in publication.index]
axes[0].bar(publication.index, publication.records, color=colors)
axes[0].set(title='공개연도별 문헌 수', xlabel='공개연도', ylabel='문헌 수')
axes[0].set_xticks(publication.index)
axes[0].tick_params(axis='x', rotation=45)
axes[1].bar(priority.index, priority.families, color='#1B4257')
axes[1].set(title='2015~2024 공개 문헌의 패밀리 최초 우선연도', xlabel='파일에서 확인한 최초 우선연도', ylabel='패밀리 수')
fig.tight_layout()
fig.savefig(figures / 'annual_counts.png', dpi=170)
plt.close(fig)
fig, ax = plt.subplots(figsize=(12, 6))
for i, period in enumerate(periods):
    values = cpc[cpc.period == period].set_index('cpc').share_percent.reindex(topcodes, fill_value=0)
    ax.bar(np.arange(len(topcodes)) + (i - .5) * .36, values, width=.36, label=f'{period} (n={denom[period]:,})', color=['#1B4257', '#087F8C'][i])
ax.set_xticks(range(len(topcodes)), topcodes, rotation=40, ha='right')
ax.set(ylabel='기간 내 패밀리 중 해당 CPC 보유 비율 (%)', title='상위 10개 H04W 주그룹의 기간별 구성')
ax.legend()
fig.tight_layout()
fig.savefig(figures / 'cpc_period_comparison.png', dpi=170)
plt.close(fig)
fig, ax = plt.subplots(figsize=(10, 7))
top = rank.head(20).iloc[::-1]
ax.barh(top.term, top.mean_tfidf, color='#087F8C')
ax.set(title=f'패밀리 {len(reps):,}개 · 정제 후 평균 TF-IDF 상위 20개', xlabel='전체 패밀리 평균 L2 정규화 TF-IDF')
fig.tight_layout()
fig.savefig(figures / 'tfidf_top20.png', dpi=170)
plt.close(fig)
print(json.dumps(stats, ensure_ascii=True, indent=2, default=int))
print('TOP20', rank.head(20).term.tolist())
