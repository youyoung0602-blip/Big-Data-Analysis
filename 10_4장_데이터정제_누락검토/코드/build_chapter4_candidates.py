from pathlib import Path
import argparse, ast, hashlib, json, re
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--inputs', type=Path, required=True)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--local', type=Path, required=True)
args = parser.parse_args()
source = args.inputs / 'missing_query_candidates_LOCAL.csv'
v2_path = args.inputs / 'v2_Lens_퀄컴_무선통신_요약전수검토_2015-2024.csv'
candidate = pd.read_csv(source).fillna('')
v2 = pd.read_csv(v2_path).fillna('')
reference_files = ['lens-export.csv', 'qualcom.csv', 'qualcom1.csv']
reference_records = pd.concat([pd.read_csv(args.inputs / p).fillna('') for p in reference_files])
references = reference_records.drop_duplicates('Lens ID')
assert candidate['Lens ID'].is_unique
assert set(candidate['Lens ID']).issubset(set(references['Lens ID']))

# Build connected family groups jointly, including intermediate reference members.
all_records = pd.concat([reference_records, v2]).reset_index(drop=True)
parent = list(range(len(all_records)))
def root(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
seen = {}
for i, row in all_records.iterrows():
    members = set(str(row['Simple Family Members']).split(';;')) | {row['Lens ID']}
    for member in members - {''}:
        if member in seen:
            parent[root(i)] = root(seen[member])
        else:
            seen[member] = i
family = dict(zip(all_records['Lens ID'], [root(i) for i in range(len(all_records))]))
v2_groups = {family[x] for x in v2['Lens ID']}
candidate['family_group'] = candidate['Lens ID'].map(family)
candidate['jurisdiction'] = candidate['Display Key'].str.split().str[0]
candidate['application_date'] = pd.to_datetime(candidate['Application Date'], errors='coerce')
candidate['year'] = candidate.application_date.dt.year
us = candidate[candidate.jurisdiction.eq('US')].copy()
period = us[us.application_date.between('2020-01-01', '2024-12-31')].copy()
overlap = period.family_group.isin(v2_groups)
outside = period[~overlap].copy()
outside['abstract_missing'] = outside.Abstract.eq('')
representatives = outside.sort_values(['abstract_missing', 'Publication Date', 'Lens ID']).drop_duplicates('family_group').copy()
def title_terms(value):
    parsed = ast.literal_eval(value)
    assert isinstance(parsed, list)
    return parsed
representatives['title_terms_parsed'] = representatives.title_terms.map(title_terms)
representatives['title_hit'] = representatives.title_terms_parsed.map(bool)
args.local.mkdir(parents=True, exist_ok=True)
representatives.to_csv(args.local / 'chapter4_candidates_LOCAL_ONLY.csv', index=False, encoding='utf-8-sig')
out = args.repo / '10_4장_데이터정제_누락검토'
tables = out / '집계표'
figures = out / '그래프'
code = out / '코드'
for folder in [tables, figures, code]:
    folder.mkdir(parents=True, exist_ok=True)
flow = pd.DataFrame([
    ['제공 후보 CSV', len(candidate), '문헌'],
    ['미국 관할', len(us), '문헌'],
    ['출원일 2020~2024', len(period), '문헌'],
    ['새 CSV와 패밀리 연결 겹침 제외', len(outside), '문헌'],
    ['관측 패밀리별 대표 문헌', len(representatives), '패밀리'],
], columns=['stage', 'count', 'unit'])
flow.to_csv(tables / 'cleaning_flow.csv', index=False, encoding='utf-8-sig')
annual = representatives.year.value_counts().reindex(range(2020, 2025), fill_value=0).sort_index().rename('representative_families').to_frame()
annual.to_csv(tables / 'candidate_year_counts.csv', encoding='utf-8-sig')
jurisdictions = candidate.jurisdiction.value_counts().rename('documents').to_frame()
jurisdictions.to_csv(tables / 'input_jurisdiction_counts.csv', encoding='utf-8-sig')
cpc_counts = Counter()
for group in representatives.family_group:
    codes = set()
    for value in outside.loc[outside.family_group == group, 'CPC Classifications']:
        codes.update(re.findall(r'\b([A-HY]\d{2}[A-Z]\d+)/', value))
    cpc_counts.update(codes)
cpc = pd.DataFrame([{'cpc': c + '/00', 'families': n, 'percent': n / len(representatives) * 100} for c, n in cpc_counts.most_common()])
cpc.to_csv(tables / 'candidate_cpc_counts.csv', index=False, encoding='utf-8-sig')
terms = Counter(t for values in representatives.title_terms_parsed for t in set(values))
pd.DataFrame([{'title_query_term': k, 'representative_families': n} for k, n in terms.most_common()]).to_csv(tables / 'title_term_counts.csv', index=False, encoding='utf-8-sig')
stats = {
    'analysis_date': '2026-11-18', 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'source_rows': len(candidate), 'us_rows': len(us), 'us_2020_2024_rows': len(period),
    'overlapping_family_rows': int(overlap.sum()), 'outside_v2_rows': len(outside),
    'candidate_families': len(representatives), 'same_family_additional_rows': len(outside) - len(representatives),
    'representative_title_hit_families': int(representatives.title_hit.sum()),
    'representative_no_title_hit_families': int((~representatives.title_hit).sum()),
    'representative_missing_abstract': int(representatives.Abstract.eq('').sum()),
    'missing_title': int(candidate.Title.eq('').sum()), 'missing_abstract': int(candidate.Abstract.eq('').sum()),
    'invalid_application_date': int(candidate.application_date.isna().sum()),
    'missing_lens_id': int(candidate['Lens ID'].eq('').sum()),
    'reference_rows_unique': len(references), 'v2_rows': len(v2),
    'v2_us_2020_2024_rows': int((v2.Jurisdiction.eq('US') & pd.to_datetime(v2['Application Date']).between('2020-01-01', '2024-12-31')).sum()),
    'relevance_review_done': False, 'live_query_verified': False,
}
(tables / 'audit_summary.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
plt.rcParams.update({'font.family': 'Malgun Gothic', 'axes.unicode_minus': False, 'font.size': 11})
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].barh(flow.stage.iloc[::-1], flow['count'].iloc[::-1], color='#087F8C')
axes[0].set(xlabel='단계별 수량 · 마지막 단계는 패밀리', title='누락 후보 목록의 범위 정리')
for y, n in enumerate(flow['count'].iloc[::-1]):
    axes[0].text(n + 8, y, f'{n:,}', va='center')
axes[0].set_xlim(0, len(candidate) * 1.15)
axes[1].bar(annual.index, annual.representative_families, color='#1B4257')
axes[1].set(title='검토 후보의 대표 문헌 출원연도', xlabel='대표 문헌 출원연도', ylabel='관측 패밀리 수')
axes[1].set_xticks(annual.index)
fig.tight_layout()
fig.savefig(figures / 'candidate_cleaning_and_years.png', dpi=170)
plt.close(fig)
baseline_dates = pd.to_datetime(v2['Application Date'])
baseline = v2[v2.Jurisdiction.eq('US') & baseline_dates.between('2020-01-01', '2024-12-31')].copy()
base_years = pd.to_datetime(baseline['Application Date']).dt.year.value_counts().reindex(range(2020, 2025), fill_value=0).sort_index()
base_years.rename('documents').to_csv(tables / 'baseline_year_counts.csv', encoding='utf-8-sig')
base_counts = Counter()
for value in baseline['CPC Classifications']:
    base_counts.update(set(re.findall(r'\b([A-HY]\d{2}[A-Z]\d+)/', value)))
base_cpc = pd.DataFrame([{'cpc': c + '/00', 'documents': n, 'percent': n / len(baseline) * 100} for c, n in base_counts.most_common()])
base_cpc.to_csv(tables / 'baseline_cpc_counts.csv', index=False, encoding='utf-8-sig')
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
axes[0].bar(base_years.index, base_years.values, color='#1B4257')
axes[0].set(title='본 분석 데이터 5,073건의 출원연도', xlabel='출원연도', ylabel='문헌 수')
axes[0].set_xticks(base_years.index)
for year, n in base_years.items():
    axes[0].text(year, n, f'{n:,}', ha='center', va='bottom')
axes[0].set_ylim(0, base_years.max() * 1.15)
top_base = base_cpc.head(10).iloc[::-1]
axes[1].barh(top_base.cpc, top_base.percent, color='#087F8C')
axes[1].set(title='본 분석 데이터의 주요 CPC', xlabel='문헌 보유 비율 (%)')
fig.tight_layout()
fig.savefig(figures / 'baseline_eda.png', dpi=170)
plt.close(fig)
year_rows = []
top_codes = base_cpc.head(10).cpc.tolist()
for year in range(2020, 2025):
    selected = baseline[pd.to_datetime(baseline['Application Date']).dt.year.eq(year)]
    counts = Counter()
    for value in selected['CPC Classifications']:
        counts.update(c + '/00' for c in set(re.findall(r'\b([A-HY]\d{2}[A-Z]\d+)/', value)))
    for c in top_codes:
        year_rows.append({'year': year, 'cpc': c, 'documents': counts[c], 'denominator': len(selected), 'percent': 100 * counts[c] / len(selected)})
year_frame = pd.DataFrame(year_rows)
year_frame.to_csv(tables / 'baseline_cpc_yearly.csv', index=False, encoding='utf-8-sig')
heat = year_frame.pivot(index='cpc', columns='year', values='percent').reindex(top_codes)
fig, ax = plt.subplots(figsize=(10, 7))
plot = ax.imshow(heat.values, cmap='Blues', vmin=0, vmax=max(70, heat.values.max()))
ax.set_xticks(range(5), range(2020, 2025))
ax.set_yticks(range(len(top_codes)), top_codes)
ax.set(title='본 분석 데이터의 출원연도별 CPC 구성', xlabel='출원연도 · 각 연도 문헌 수를 분모로 계산')
for i in range(len(top_codes)):
    for j in range(5):
        value = heat.iloc[i, j]
        ax.text(j, i, f'{value:.1f}%', ha='center', va='center', color='white' if value > 40 else '#142D40')
fig.colorbar(plot, ax=ax, label='문헌 보유 비율 (%)')
fig.tight_layout()
fig.savefig(figures / 'baseline_cpc_yearly.png', dpi=170)
plt.close(fig)
fig, ax = plt.subplots(figsize=(10, 6))
top = cpc.head(10).iloc[::-1]
ax.barh(top.cpc, top.percent, color='#087F8C')
ax.set(title=f'누락 검토 후보 {len(representatives):,}개 패밀리의 상위 CPC', xlabel='후보 패밀리 중 해당 CPC 보유 비율 (%)')
fig.tight_layout()
fig.savefig(figures / 'candidate_cpc.png', dpi=170)
plt.close(fig)
assert len(candidate) == 1152 and len(period) == int(overlap.sum()) + len(outside)
assert annual.representative_families.sum() == len(representatives)
print(json.dumps(stats, ensure_ascii=True, indent=2))
print('YEARS', annual.to_json())
print('CPC', cpc.head(10).to_json(orient='records'))
for _, row in representatives[representatives.title_hit].head(10).iterrows():
    print(json.dumps({k: row[k] for k in ['Display Key', 'Title', 'Abstract', 'Application Date', 'URL', 'title_terms']}, ensure_ascii=True))
