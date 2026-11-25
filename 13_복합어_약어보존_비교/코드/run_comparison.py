from pathlib import Path
import ast,json,re,zipfile
import numpy as np,pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--inputs', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
B=args.inputs;O=args.output;O.mkdir(parents=True,exist_ok=True)
CODE=Path(__file__).resolve().parent
REPO=CODE.parents[1]
nb=json.loads((REPO/'12_Colab코드_시각화/code/analysis.ipynb').read_text(encoding='utf-8'))
node=ast.parse(''.join(nb['cells'][3]['source']))
extra=next(ast.literal_eval(x.value.args[0]) for x in node.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Attribute) and x.value.func.attr=='update')
stop=set((CODE/'english_stopwords.txt').read_text(encoding='utf-8').split())|set(extra)
d=pd.read_csv(B/'v2_Lens_퀄컴_무선통신_요약전수검토_2015-2024.csv').fillna('');d=d[d['Application Date'].between('2020-01-01','2024-12-31')];d=d.assign(_b=d.Kind.str.startswith('B')).sort_values('_b',ascending=False).drop_duplicates('Application Number').reset_index(drop=True)
text=d.Title+' '+d.Abstract;years=pd.to_datetime(d['Application Date']).dt.year
oldkeep={'bwp','csi','dci','ack','cqi','rrc','mac','phy','qos','lte','v2x'}
newkeep={'nr','dci','bwp','ack','rrc','mac','phy','qos','lte','cqi','tci','ssb','srs','iab','ris','pc5','v2x','5g','4g','harq'}
rules=[(r'\brandom[\s-]+access[\s-]+preambles?\b','random_access_preamble'),(r'\bchannel[\s-]+state[\s-]+information\b|\bcsi\b','channel_state_information'),(r'\bbeam[\s-]+failure[\s-]+recovery\b','beam_failure_recovery'),(r'\bnon[\s-]*terrestrial[\s-]+networks?\b|\bntn\b','non_terrestrial_network'),(r'\breference[\s-]+signals?\b','reference_signal'),(r'\brandom[\s-]+access\b','random_access'),(r'\bresource[\s-]+pools?\b','resource_pool'),(r'\bconfigured[\s-]+grants?\b','configured_grant'),(r'\bbeam[\s-]+management\b','beam_management'),(r'\bcarrier[\s-]+aggregation\b','carrier_aggregation'),(r'\bdual[\s-]+connectivity\b','dual_connectivity')]
def old(s):return ' '.join(w.lower() for w in re.sub('[^a-zA-Z]',' ',s).split() if (len(w)>3 or w.lower() in oldkeep) and w.lower() not in stop)
def new(s):
 s=re.sub('[‐‑‒–—−]','-',s.lower())
 for pat,rep in rules:s=re.sub(pat,rep,s)
 return ' '.join(w for w in re.findall(r'\b[a-z0-9]+(?:_[a-z0-9]+)*\b',s) if not w.isdigit() and (len(w)>3 or w in newkeep) and w not in stop)
results=[]
for clean in [old,new]:
 texts=text.map(clean);v=TfidfVectorizer(stop_words='english',max_features=1000,max_df=.5);X=v.fit_transform(texts);m=NMF(n_components=7,random_state=42,max_iter=500);W=m.fit_transform(X);labels=W.argmax(1);terms=v.get_feature_names_out();results.append((texts,v,X,m,W,labels,terms));print(clean.__name__,X.shape,np.bincount(labels),flush=True)
a,b=results;cross=pd.crosstab(a[5],b[5]).reindex(index=range(7),columns=range(7),fill_value=0).values;ri,ci=linear_sum_assignment(-cross);mapping=dict(zip(ci,ri));aligned=np.array([mapping[x] for x in b[5]]);names=['사이드링크','CSI','랜덤 액세스','HARQ','빔','스케줄링','이동성']
rows=[]
for i in range(7):
 j=int(ci[np.where(ri==i)[0][0]]);words=b[6][np.argsort(-b[3].components_[j])[:12]].tolist();oldwords=a[6][np.argsort(-a[3].components_[i])[:8]].tolist();rows.append({'topic':i+1,'baseline_label':names[i],'old_count':int((a[5]==i).sum()),'new_matched_count':int((aligned==i).sum()),'new_label':['사이드링크','CSI·참조 신호','BWP·대역 운용','HARQ','빔 관리','접속·스케줄링','이동성'][i],'old_keywords':', '.join(oldwords),'new_keywords':', '.join(words)})
pd.DataFrame(rows).to_csv(O/'topics.csv',index=False,encoding='utf-8-sig')
termscheck=['channel_state_information','reference_signal','random_access','random_access_preamble','resource_pool','configured_grant','beam_management','beam_failure_recovery','carrier_aggregation','dual_connectivity','non_terrestrial_network','nr','ntn','v2x','pc5','tci','ssb','srs','5g']
checks=[]
for term in termscheck:
 row={'term':term}
 for tag,r in zip(['old','new'],results):
  row[tag+'_preprocessed_df']=int(r[0].map(lambda s:term in s.split()).sum());row[tag+'_in_vocabulary']=term in set(r[6])
 checks.append(row)
pd.DataFrame(checks).to_csv(O/'term_preservation.csv',index=False,encoding='utf-8-sig')
stats={'documents':len(d),'annual_counts':years.value_counts().sort_index().to_dict(),'agreement_after_matching':float(np.mean(aligned==a[5])),'adjusted_rand_index':float(adjusted_rand_score(a[5],b[5])),'old_empty_rows':int((a[2].getnnz(axis=1)==0).sum()),'new_empty_rows':int((b[2].getnnz(axis=1)==0).sum()),'baseline_counts_match_notebook':np.bincount(a[5]).tolist()==[1324,609,341,552,548,1066,604]}
(O/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8');(O/'settings.json').write_text(json.dumps({'rules':rules,'extra_stopwords':extra,'new_short_terms':sorted(newkeep)},ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
fig,ax=plt.subplots(figsize=(13,6));x=np.arange(7);ax.bar(x-.2,[r['old_count'] for r in rows],.4,label='기존 전처리 · 로컬 재실행');ax.bar(x+.2,[r['new_matched_count'] for r in rows],.4,label='복합어·약어 보존');ax.set_xticks(x,[f'{r["baseline_label"]} → {r["new_label"]}' for r in rows],rotation=15);ax.set(ylabel='문헌 수',title='전처리 변경 전후 토픽 구성 · 문헌 중첩으로 토픽 대응');ax.legend();fig.tight_layout();fig.savefig(O/'topic_comparison.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(13,7));c=pd.DataFrame(checks).iloc[::-1];ax.barh(c.term,c.new_preprocessed_df,color=['#087f8c' if ok else '#e3aa42' for ok in c.new_in_vocabulary]);ax.set(title='개선 전처리 후 기술어 보존 · 청록은 TF-IDF 포함, 노랑은 특성 제한에서 제외',xlabel='해당 토큰이 남은 문헌 수');fig.tight_layout();fig.savefig(O/'term_preservation.png',dpi=170);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,7));norm=cross[:,ci]/cross.sum(axis=1,keepdims=True)*100;im=ax.imshow(norm,cmap='Blues',vmin=0,vmax=100);ax.set_xticks(range(7),[f'대응 T{i+1}' for i in ri]);ax.set_yticks(range(7),[f'T{i+1} {n}' for i,n in enumerate(names)]);ax.set(xlabel='개선 모델 토픽',ylabel='기존 모델 토픽',title='기존 토픽 문헌이 개선 모델에서 배정된 비율 (%)')
for i in range(7):
 for j in range(7):ax.text(j,i,f'{norm[i,j]:.1f}',ha='center',va='center',color='white' if norm[i,j]>50 else 'black')
fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(O/'topic_migration.png',dpi=170);plt.close(fig)
annual=pd.crosstab(years,aligned).reindex(columns=range(7),fill_value=0);annual.div(annual.sum(axis=1),axis=0).mul(100).to_csv(O/'new_yearly_shares.csv',encoding='utf-8-sig')
print(json.dumps(stats,ensure_ascii=True),flush=True);print(pd.DataFrame(rows).to_string(index=False),flush=True)
