from pathlib import Path
import re, json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd()
OUT=BASE/'qualcomm_analysis'/'pc10_refined'; OUT.mkdir(parents=True,exist_ok=True)
r=pd.read_csv(BASE/'qualcomm_analysis'/'family_topics.csv').fillna('')
codes=r['CPC Classifications'].map(lambda s:set(re.findall(r'\b[A-HY]\d{2}[A-Z]',s)))
frequency={c:sum(c in x for x in codes) for c in set().union(*codes)}
top=sorted(frequency,key=lambda c:(-frequency[c],c))[:10]
mask=codes.map(lambda x:bool(x.intersection(top)))
r=r[mask].copy(); codes=codes[mask]
# Display label only: first matching code in the overall frequency ranking.
r['display_cpc']=codes.map(lambda x:next(c for c in top if c in x))
old_stop=set(ENGLISH_STOP_WORDS)|set('method methods apparatus system systems device devices embodiment embodiments invention present disclosure disclosed provided providing comprises comprising includes including plurality thereof configured said respective corresponding based using used use wherein having associated example examples aspect aspects techniques described relating relates patent second first third determining determine include multiple certain provide dwg cl substance effect'.split())
extra=set('data information set sets current value values obtain obtained obtaining receive received receiving transmit transmitted transmitting perform performed performing operation operations processing process processes enable enabled enabling comprise include respective respectively according thereof therein thereto least substantially particular generally different additional alternatively suitable comprising configuration configured'.split())
rules=[
 (r'\buser equipment(?:s)?(?:\s*\(ue\))?\b|\bues?\b','user_equipment'),
 (r'\bbase stations?\b','base_station'),
 (r'\bneural networks?\b','neural_network'),
 (r'\bmachine learning\b','machine_learning'),
 (r'\bvideo cod(?:ing|er|ers)\b','video_coding'),
 (r'\bpoint clouds?\b','point_cloud'),
 (r'\btouch panels?\b','touch_panel'),
 (r'\bmems\b|\bmicroelectromechanical systems?\b','microelectromechanical'),
]
plural={'images':'image','objects':'object','models':'model','channels':'channel','signals':'signal','frames':'frame','blocks':'block','sensors':'sensor','electrodes':'electrode','networks':'network','transducers':'transducer','layers':'layer','circuits':'circuit','beams':'beam','streams':'stream','resources':'resource','antennas':'antenna','processors':'processor','memories':'memory','features':'feature','packets':'packet','frequencies':'frequency'}
def clean(s):
    s=s.lower()
    for pattern,replacement in rules: s=re.sub(pattern,replacement,s)
    s=re.sub(r'\b[a-z]+\b',lambda m:plural.get(m[0],m[0]),s)
    s=' '.join(t for t in re.findall(r'\b[a-z][a-z_]+\b',s) if t not in old_stop|extra)
    s=re.sub(r'\b([a-z_]+)(?:\s+\1\b)+',r'\1',s)
    return s
def fit(refined):
    v=TfidfVectorizer(stop_words=sorted(old_stop|extra if refined else old_stop),ngram_range=(1,2),min_df=5 if refined else 3,max_df=.7 if refined else .85,sublinear_tf=True,strip_accents='unicode',token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z_]+\b' if refined else r'(?u)\b[a-zA-Z][a-zA-Z]+\b')
    X=v.fit_transform(r.analysis_text.map(clean) if refined else r.analysis_text)
    p=PCA(n_components=10,svd_solver='full'); z=p.fit_transform(X.toarray())
    for j in range(10):
        if p.components_[j,np.abs(p.components_[j]).argmax()]<0: p.components_[j]*=-1; z[:,j]*=-1
    assert np.allclose(z.mean(axis=0),0,atol=1e-10)
    assert np.allclose(p.components_@p.components_.T,np.eye(10),atol=1e-10)
    assert np.allclose(z.var(axis=0,ddof=1),p.explained_variance_)
    return v,X,p,z
v0,X0,p0,z0=fit(False)
print('Baseline PCA completed',flush=True)
v,X,p,z=fit(True); terms=v.get_feature_names_out()
ev=p.explained_variance_ratio_; cum=ev.cumsum()
table=pd.DataFrame({'PC':[f'PC{i+1}' for i in range(10)],'eigenvalue':p.explained_variance_,'explained_percent':ev*100,'cumulative_percent':cum*100,'baseline_explained_percent':p0.explained_variance_ratio_*100,'baseline_cumulative_percent':p0.explained_variance_ratio_.cumsum()*100,'within_retained_10_percent':ev/ev.sum()*100})
table.to_csv(OUT/'pc10_variance.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(p.components_.T,index=terms,columns=table.PC).rename_axis('term').to_csv(OUT/'pc10_term_coefficients.csv',encoding='utf-8-sig')
local=r[['family_group','Lens ID','Title','URL','display_cpc']].copy()
for j in range(10):local[f'PC{j+1}']=z[:,j]
local.to_csv(OUT/'pc10_document_scores_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
cp=pd.DataFrame({'CPC':top,'families':[frequency[c] for c in top]})
cp.to_csv(OUT/'top10_cpc_counts.csv',index=False,encoding='utf-8-sig')
axes_info=[]
for j in range(10):
 c=p.components_[j]
 axes_info.append({'PC':j+1,'positive':terms[c.argsort()[-10:][::-1]].tolist(),'negative':terms[c.argsort()[:10]].tolist()})
result={'source_families':658,'selected_families':len(r),'excluded_families':658-len(r),'baseline_terms':X0.shape[1],'refined_terms':X.shape[1],'top_cpc':cp.to_dict('records'),'axes':axes_info,'variance':table.to_dict('records'),'normalization_rules':rules,'plural_mapping':plural,'additional_stopwords':sorted(extra)}
(OUT/'pc10_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
fig,ax=plt.subplots(figsize=(11,6))
ax.plot(range(1,11),p0.explained_variance_ratio_.cumsum()*100,'o--',label=f'정제 전 ({X0.shape[1]:,}개 특성)')
ax.plot(range(1,11),cum*100,'o-',label=f'정제 후 ({X.shape[1]:,}개 특성)')
ax.set_xticks(range(1,11));ax.set_xlabel('유지하는 주성분 수');ax.set_ylabel('전체 분산 대비 누적 설명분산 (%)');ax.set_title(f'상위 10개 CPC 포함 문헌 {len(r)}개: 용어 정제 전후 비교');ax.legend();ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(OUT/'pc10_cumulative_variance.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(17,7))
for ax,(a,b) in zip(axs,[(0,1),(2,3)]):
 for k,c in enumerate(top):
  m=r.display_cpc.eq(c).to_numpy()
  if m.any():ax.scatter(z[m,a],z[m,b],s=22,alpha=.65,label=f'{c} (n={m.sum()})',color=plt.get_cmap('tab10')(k))
 ax.axhline(0,color='gray',lw=.6);ax.axvline(0,color='gray',lw=.6);ax.set_xlabel(f'PC{a+1} ({ev[a]:.2%})');ax.set_ylabel(f'PC{b+1} ({ev[b]:.2%})');ax.grid(alpha=.15)
axs[0].legend(fontsize=8);axs[0].set_title('정제 후 PC1·PC2');axs[1].set_title('정제 후 PC3·PC4')
fig.suptitle('10개 주성분 중 첫 4개 축의 기술지도 — 색상은 표시용 CPC 우선 배정')
fig.tight_layout();fig.savefig(OUT/'pc10_technology_maps.png',dpi=180);plt.close(fig)
print(json.dumps({k:result[k] for k in ['selected_families','excluded_families','baseline_terms','refined_terms','axes','variance']},ensure_ascii=True,indent=2))
