from pathlib import Path
import ast, json
import numpy as np
import pandas as pd
from scipy.linalg import eigh, subspace_angles
from scipy.spatial.distance import cdist
from sklearn.metrics import pairwise_distances
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd(); OUT=BASE/'qualcomm_analysis'/'clear_results'; OUT.mkdir(parents=True,exist_ok=True)
# Reuse the recorded selection and cleaning rules, without running the original PCA pipeline.
source=Path(__file__).resolve().with_name('qualcomm_pc10.py')
tree=ast.parse(source.read_text(encoding='utf-8'))
prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name=='fit': break
    prefix.append(node)
ctx={'__file__':str(source)}
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'),ctx)
r=ctx['r']; codes=ctx['codes']; top=ctx['top']; text=r.analysis_text.map(ctx['clean']); stop=sorted(ctx['old_stop']|ctx['extra'])
def calculate(min_df):
    v=TfidfVectorizer(stop_words=stop,ngram_range=(1,2),min_df=min_df,max_df=.7,sublinear_tf=True,strip_accents='unicode',token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z_]+\b')
    X=v.fit_transform(text)
    A=X.toarray(); A-=A.mean(axis=0)
    vals,U=eigh(A@A.T/(len(r)-1)); idx=np.argsort(vals)[::-1]; vals=np.maximum(vals[idx],0); U=U[:,idx]
    ev=vals/vals.sum(); scores=U*np.sqrt(vals*(len(r)-1))
    return v,X,ev,U,scores
v,X,ev,U,scores=calculate(5)
old=json.loads((BASE/'qualcomm_analysis'/'pc10_refined'/'pc10_results.json').read_text(encoding='utf-8'))
assert np.allclose(ev[:10]*100,[row['explained_percent'] for row in old['variance']],atol=1e-8)
cum=ev.cumsum(); thresholds={str(t):int(np.searchsorted(cum,t/100)+1) for t in [50,70,80,90]}
pd.DataFrame({'PC':np.arange(1,len(ev)+1),'explained_percent':ev*100,'cumulative_percent':cum*100}).to_csv(OUT/'full_variance_spectrum.csv',index=False,encoding='utf-8-sig')
def neighbors(dist,k=10):
    dist=dist.copy(); np.fill_diagonal(dist,np.inf)
    return np.argsort(dist,axis=1,kind='stable')[:,:k]
reference=neighbors(pairwise_distances(X,metric='euclidean'))
preservation=[]
for k in [2,10,50]:
    projected=neighbors(cdist(scores[:,:k],scores[:,:k]))
    overlap=np.array([len(set(a)&set(b))/10 for a,b in zip(reference,projected)])
    preservation.append({'retained_PCs':k,'cumulative_variance_percent':float(cum[k-1]*100),'mean_neighbor10_overlap_percent':float(overlap.mean()*100),'median_neighbor10_overlap_percent':float(np.median(overlap)*100)})
pd.DataFrame(preservation).to_csv(OUT/'neighbor_preservation.csv',index=False,encoding='utf-8-sig')
sensitivity=[]
for threshold in [3,5,8]:
    if threshold==5: vt,Xt,evt,Ut,st=v,X,ev,U,scores
    else: vt,Xt,evt,Ut,st=calculate(threshold)
    angles=subspace_angles(U[:,:10],Ut[:,:10])
    sensitivity.append({'min_df':threshold,'features':Xt.shape[1],'PC1_PC2_variance_percent':float(evt[:2].sum()*100),'PC1_PC10_variance_percent':float(evt[:10].sum()*100),'PC10_subspace_overlap_vs_min_df5_percent':float(np.mean(np.cos(angles)**2)*100)})
    print(f'Sensitivity min_df={threshold} complete',flush=True)
pd.DataFrame(sensitivity).to_csv(OUT/'cleaning_sensitivity.csv',index=False,encoding='utf-8-sig')
terms=v.get_feature_names_out(); means=[]; keyword_rows=[]; picked=[]
membership=np.array([[c in cs for c in top] for cs in codes])
for j,c in enumerate(top):
    m=membership[:,j]
    avg=np.asarray(X[m].mean(axis=0)).ravel(); other=np.asarray(X[~m].mean(axis=0)).ravel()
    means.append(avg)
    # Unigrams include normalized technical phrase tokens; avoid duplicate nested n-grams.
    eligible=np.array([' ' not in t for t in terms])
    contrast=avg-other; idx=np.where(eligible)[0]; idx=idx[np.argsort(contrast[idx])[::-1]][:5]
    picked.extend(idx[:3])
    for rank,i in enumerate(idx,1):keyword_rows.append({'CPC':c,'families':int(m.sum()),'rank':rank,'term':terms[i],'within_mean_tfidf':float(avg[i]),'outside_mean_tfidf':float(other[i]),'difference':float(contrast[i])})
pd.DataFrame(keyword_rows).to_csv(OUT/'cpc_distinctive_keywords.csv',index=False,encoding='utf-8-sig')
co=membership.astype(int).T@membership.astype(int)
pd.DataFrame(co,index=top,columns=top).rename_axis('CPC').to_csv(OUT/'cpc_cooccurrence_counts.csv',encoding='utf-8-sig')
multi=int((membership.sum(axis=1)>1).sum())
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
fig,axs=plt.subplots(1,2,figsize=(15,6))
axs[0].plot(np.arange(1,len(cum)+1),cum*100);axs[0].axvline(10,color='#c26632',ls='--',label=f'PC10: {cum[9]:.2%}');axs[0].set_xlabel('유지 주성분 수');axs[0].set_ylabel('누적 설명분산 (%)');axs[0].set_title('전체 분산을 얼마나 보존하는가');axs[0].legend();axs[0].grid(alpha=.2)
for t,k in thresholds.items():axs[0].scatter(k,int(t),s=25);axs[0].annotate(f'{t}%: {k}개',(k,int(t)),xytext=(4,-13),textcoords='offset points',fontsize=9)
axs[1].bar([str(x['retained_PCs']) for x in preservation],[x['mean_neighbor10_overlap_percent'] for x in preservation],color=['#aaa','#347ab7','#449b86']);axs[1].set_xlabel('유지 주성분 수');axs[1].set_ylabel('원래 최근접 10개 문헌 보존율 (%)');axs[1].set_ylim(0,100);axs[1].set_title('투영 후 이웃 관계 보존 — 분류 정확도가 아님')
for i,x in enumerate(preservation):axs[1].text(i,x['mean_neighbor10_overlap_percent']+2,f"{x['mean_neighbor10_overlap_percent']:.1f}%",ha='center')
fig.tight_layout();fig.savefig(OUT/'projection_quality.png',dpi=180);plt.close(fig)
picked=list(dict.fromkeys(picked)); mat=np.array(means)[:,picked]; norm=mat/np.maximum(mat.max(axis=0),1e-12)
fig,ax=plt.subplots(figsize=(16,7));im=ax.imshow(norm,cmap='Blues',aspect='auto',vmin=0,vmax=1)
ax.set_xticks(range(len(picked)),terms[picked],rotation=60,ha='right',fontsize=9);ax.set_yticks(range(10),[f'{c} (n={membership[:,i].sum()})' for i,c in enumerate(top)])
ax.set_title('상위 10개 CPC 분야의 특징 용어\n각 용어 열의 최고 평균을 1로 정규화 — 색상은 분야 비중·확률이 아님');fig.colorbar(im,ax=ax,label='용어별 상대 평균 TF-IDF');fig.tight_layout();fig.savefig(OUT/'cpc_keyword_heatmap.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,8));jaccard=co/(np.diag(co)[:,None]+np.diag(co)[None,:]-co)
im=ax.imshow(jaccard,cmap='YlGnBu',vmin=0,vmax=1);ax.set_xticks(range(10),top,rotation=45);ax.set_yticks(range(10),top)
for i in range(10):
 for j in range(10):ax.text(j,i,f'{jaccard[i,j]:.2f}',ha='center',va='center',color='white' if jaccard[i,j]>.55 else 'black',fontsize=9)
ax.set_title('CPC 분야 중복: Jaccard = 교집합 / 합집합');fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(OUT/'cpc_overlap.png',dpi=180);plt.close(fig)
result={'documents':len(r),'features':X.shape[1],'threshold_components':thresholds,'neighbor_preservation':preservation,'sensitivity':sensitivity,'multi_cpc_documents':multi,'field_keywords':keyword_rows}
(OUT/'quality_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:val for k,val in result.items() if k!='field_keywords'},ensure_ascii=True,indent=2))
