from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('qualcomm_analysis')
r=pd.read_csv(OUT/'family_topics.csv').fillna('')
stop=set(ENGLISH_STOP_WORDS)|set('method methods apparatus system systems device devices embodiment embodiments invention present disclosure disclosed provided providing comprises comprising includes including plurality thereof configured said respective corresponding based using used use wherein having associated example examples aspect aspects techniques described relating relates patent second first third determining determine include multiple certain provide dwg cl substance effect'.split())
vectorizer=TfidfVectorizer(stop_words=sorted(stop),ngram_range=(1,2),min_df=3,max_df=.85,sublinear_tf=True,strip_accents='unicode',token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]+\b')
X=vectorizer.fit_transform(r.analysis_text)
terms=vectorizer.get_feature_names_out()
# PCA centers columns; no per-term variance scaling. This is not uncentered TruncatedSVD.
pca=PCA(n_components=2,svd_solver='full')
scores=pca.fit_transform(X.toarray())
for j in range(2):
    # Deterministic sign convention: the largest absolute coefficient is positive.
    if pca.components_[j,np.abs(pca.components_[j]).argmax()]<0:
        pca.components_[j]*=-1; scores[:,j]*=-1
assert np.isfinite(scores).all() and np.allclose(scores.mean(axis=0),0,atol=1e-10)
assert np.allclose(pca.components_@pca.components_.T,np.eye(2),atol=1e-10)
r['PC1']=scores[:,0]; r['PC2']=scores[:,1]
r['quadrant']=np.select([(scores[:,0]>=0)&(scores[:,1]>=0),(scores[:,0]<0)&(scores[:,1]>=0),(scores[:,0]<0)&(scores[:,1]<0)],['Q1 (+,+)','Q2 (-,+)','Q3 (-,-)'],default='Q4 (+,-)')
cols=['family_group','Lens ID','Title','URL','topic','PC1','PC2','quadrant']
r[cols].to_csv(OUT/'pca_patent_scores.csv',index=False,encoding='utf-8-sig')
load=pd.DataFrame({'term':terms,'PC1_coefficient':pca.components_[0],'PC2_coefficient':pca.components_[1]})
load.to_csv(OUT/'pca_term_coefficients.csv',index=False,encoding='utf-8-sig')
names=['단말·기지국 및 빔 제어','비디오 코딩','컴퓨터 비전·3차원 인식','터치 센싱','무선 채널·전송 제어','음향·MEMS·관련 회로','AI·머신러닝·관련 연산','오디오·공간음향']
plt.rcParams['font.family']='Malgun Gothic'
plt.rcParams['axes.unicode_minus']=False
fig,ax=plt.subplots(figsize=(13,9))
for k,name in enumerate(names):
    mask=r.topic==k
    ax.scatter(r.loc[mask,'PC1'],r.loc[mask,'PC2'],s=32,alpha=.68,label=f'{name} (n={mask.sum()})',color=plt.get_cmap('tab10')(k))
ax.axhline(0,color='gray',lw=.7); ax.axvline(0,color='gray',lw=.7)
ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.2%})')
ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.2%})')
ax.set_title('퀄컴 특허 기술 지도: TF-IDF → PCA\n점 하나 = 패밀리 대표 문헌, 색상 = 기존 NMF 주제')
ax.legend(loc='best',fontsize=9); ax.grid(alpha=.15)
fig.tight_layout(); fig.savefig(OUT/'pca_technology_map.png',dpi=180); plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(15,8))
for j,ax in enumerate(axes):
    c=pca.components_[j]; idx=np.r_[c.argsort()[:10],c.argsort()[-10:]]
    idx=idx[np.argsort(c[idx])]
    ax.barh(terms[idx],c[idx],color=['#c26632' if a<0 else '#347ab7' for a in c[idx]])
    ax.set_title(f'PC{j+1}: 양·음 방향 상위 단어 계수'); ax.axvline(0,color='gray',lw=.7)
fig.tight_layout(); fig.savefig(OUT/'pca_term_directions.png',dpi=180); plt.close(fig)
summary={'n':len(r),'features':len(terms),'explained_variance_ratio':pca.explained_variance_ratio_.tolist(),'axes':[],'quadrants':{}}
for j in range(2):
    c=pca.components_[j]
    summary['axes'].append({'pc':j+1,'positive':terms[c.argsort()[-12:][::-1]].tolist(),'negative':terms[c.argsort()[:12]].tolist()})
for q,g in r.groupby('quadrant'):
    summary['quadrants'][q]={'n':len(g),'topics':{names[int(k)]:int(v) for k,v in g.topic.value_counts().items()}}
(OUT/'pca_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True,indent=2))
