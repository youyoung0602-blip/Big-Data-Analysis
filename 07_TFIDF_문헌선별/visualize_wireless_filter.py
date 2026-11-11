from pathlib import Path
import re,json
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd();OUT=BASE/'qualcom_tfidf_filter';OUT.mkdir(exist_ok=True)
d=pd.read_csv(BASE/'qualcom.csv').fillna('')
stop=set(ENGLISH_STOP_WORDS)|set('method methods apparatus system systems device devices embodiment embodiments invention present disclosure disclosed provided providing comprises comprising includes including plurality thereof configured said respective corresponding based using used use wherein having associated example examples aspect aspects techniques described relating relates patent first second third determining determine include multiple certain provide obtaining obtained obtain'.split())
maps={'channels':'channel','signals':'signal','networks':'network','resources':'resource','antennas':'antenna','devices':'device','transmissions':'transmission','stations':'station','beams':'beam','packets':'packet','receivers':'receiver','transmitters':'transmitter','communications':'communication','wirelessly':'wireless','frequencies':'frequency'}
def clean(s):
    s=s.lower()
    s=re.sub(r'\buser equipments?\b|\bues?\b','user_equipment',s)
    s=re.sub(r'\bbase stations?\b','base_station',s)
    s=re.sub(r'\bwi[ -]?fi\b','wifi',s)
    return re.sub(r'\b[a-z]+\b',lambda m:maps.get(m[0],m[0]),s)
text=(d.Title+' '+d.Abstract).map(clean)
v=TfidfVectorizer(stop_words=sorted(stop),ngram_range=(1,2),min_df=2,max_df=.85,sublinear_tf=True,strip_accents='unicode',token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z_]+\b')
X=v.fit_transform(text)
# Reference text is an explicit relevance criterion, not an external relevance label.
reference='''wireless communication radio cellular LTE NR 5G WLAN wifi bluetooth
user_equipment base_station uplink downlink sidelink channel radio resource
allocation scheduling transmission reception antenna beamforming beam MIMO OFDM
random access handover synchronization reference signal channel estimation
power control spectrum frequency carrier modulation coding network protocol
packet mesh relay DRX HARQ CQI access point
subframe frame slot paging RACH PRACH PDCCH PUCCH PUSCH RRC MAC
control information carrier aggregation bandwidth beam sweep random access
channel state information radio link cell selection reselection multicast broadcast'''
q=v.transform([clean(reference)])
assert q.nnz>0
score=cosine_similarity(X,q).ravel()
features=X.getnnz(axis=1)
threshold=float(np.quantile(score,.10))
low=score<=threshold
short=features<10
candidate=low|short
status=np.where(candidate,'검토 후보','유지 우선')
d['topic_relevance_cosine']=score;d['tfidf_nonzero_features']=features;d['review_status']=status
d['review_reason']=np.select([low&short,low,short],['관련도 하위 10% 및 유효 특성 10개 미만','관련도 하위 10%','유효 특성 10개 미만'],default='후보 기준에 해당하지 않음')
d['low_relevance_percentile']=pd.Series(score).rank(pct=True,method='average')*100
# Full row-level information stays local; it is not copied into the public repository.
cols=['Lens ID','Title','URL','topic_relevance_cosine','tfidf_nonzero_features','low_relevance_percentile','review_status','review_reason']
d.sort_values('topic_relevance_cosine')[cols].to_csv(OUT/'문헌별_TFIDF_선별점수_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
d.loc[~candidate].to_csv(OUT/'유지우선_문헌_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
d.loc[candidate].to_csv(OUT/'검토후보_문헌_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
pd.DataFrame({'relevance_lower':np.histogram(score,bins=25)[1][:-1],'relevance_upper':np.histogram(score,bins=25)[1][1:],'documents':np.histogram(score,bins=25)[0]}).to_csv(OUT/'score_histogram.csv',index=False,encoding='utf-8-sig')
sensitivity=[]
for pct in [5,10,15,20]:
    t=float(np.quantile(score,pct/100));m=(score<=t)|short
    sensitivity.append({'bottom_percent_setting':pct,'cosine_threshold':t,'review_candidates':int(m.sum()),'retain_priority':int((~m).sum())})
pd.DataFrame(sensitivity).to_csv(OUT/'threshold_sensitivity.csv',index=False,encoding='utf-8-sig')
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
blue='#3578b5';orange='#dc8743'
fig,axs=plt.subplots(2,2,figsize=(16,11))
ax=axs[0,0];ax.hist(score,bins=25,color=blue,edgecolor='white');ax.axvline(threshold,color=orange,lw=2,ls='--',label=f'하위 10% 경계: {threshold:.3f}');ax.set_xlabel('무선통신 기준문과의 TF-IDF 코사인 관련도');ax.set_ylabel('문헌 수');ax.set_title('① 주제 관련도가 낮은 문헌을 먼저 검토');ax.legend(fontsize=9)
ax=axs[0,1]
ax.scatter(score[~candidate],features[~candidate],s=20,alpha=.5,c=blue,label=f'유지 우선 {int((~candidate).sum())}건')
ax.scatter(score[candidate],features[candidate],s=30,alpha=.8,c=orange,label=f'검토 후보 {int(candidate.sum())}건')
ax.axvline(threshold,color=orange,ls='--');ax.axhline(10,color='gray',ls=':');ax.set_xlabel('무선통신 주제 관련도');ax.set_ylabel('유효 TF-IDF 특성 수 (내용량 보조지표)');ax.set_title('② 낮은 관련도와 부족한 텍스트를 구분');ax.legend(fontsize=9)
ax=axs[1,0];idx=np.argsort(score);rank=np.arange(1,len(d)+1)
ax.plot(rank,score[idx],color=blue,lw=2);ax.scatter(rank[candidate[idx]],score[idx][candidate[idx]],color=orange,s=9);ax.axhline(threshold,color=orange,ls='--');ax.set_xlabel('주제 관련도 오름차순 문헌 순위');ax.set_ylabel('TF-IDF 코사인 관련도');ax.set_title('③ 왼쪽의 낮은 점수부터 검토 — 점수는 가치가 아님')
ax=axs[1,1];ax.barh(['전체 입력','유지 우선','검토 후보'],[len(d),int((~candidate).sum()),int(candidate.sum())],color=['#8895a3',blue,orange]);ax.invert_yaxis();ax.set_xlim(0,len(d)*1.18);ax.set_xlabel('문헌 수');ax.set_title('④ 검토 후보를 분리하고 원본은 보존')
for i,n in enumerate([len(d),int((~candidate).sum()),int(candidate.sum())]):ax.text(n+12,i,f'{n:,}건',va='center')
fig.suptitle('qualcom.csv: TF-IDF 기반 무선통신 문헌 선별\n주제 관련도가 낮은 문헌을 검토 후보로 표시 — 특허 중요도·가치 판정이 아님',fontsize=16)
fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(OUT/'tfidf_document_filter.png',dpi=180);plt.close(fig)
assert len(d)==int(candidate.sum())+int((~candidate).sum())
assert np.isfinite(score).all() and score.min()>=-1e-9 and score.max()<=1+1e-9
result={'documents':len(d),'features':X.shape[1],'review_candidates':int(candidate.sum()),'retain_priority':int((~candidate).sum()),'low_relevance_candidates':int(low.sum()),'short_text_candidates':int(short.sum()),'threshold':threshold,'score_min':float(score.min()),'score_median':float(np.median(score)),'score_max':float(score.max()),'reference_text':reference,'threshold_sensitivity':sensitivity,'note':'10% is an exploratory review budget, not a validated accuracy threshold.'}
(OUT/'filter_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True,indent=2))
print('LOW SCORE EXAMPLES (local review only):')
for _,row in d.sort_values('topic_relevance_cosine').head(12).iterrows():print(ascii(row.Title),round(row.topic_relevance_cosine,4))
