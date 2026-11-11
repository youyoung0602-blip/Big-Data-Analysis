from pathlib import Path
import json,re,hashlib
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from scipy.sparse import save_npz
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd();LOCAL=BASE/'query_refinement_steps';LOCAL.mkdir(exist_ok=True)
PUBLIC=BASE/'Big-Data-Analysis'/'08_검색식개선_단계별'/'02_용어정제_TFIDF';PUBLIC.mkdir(parents=True,exist_ok=True)
source=LOCAL/'step01_family_representatives_LOCAL_ONLY.csv'
d=pd.read_csv(source).fillna('');text=d.Title+' '+d.Abstract
patent_stop=set('method methods apparatus system systems device devices embodiment embodiments invention present disclosure disclosed provide provides provided providing comprise comprises comprising include includes including plurality thereof therein thereto wherein said respective respectively corresponding according example examples aspect aspects technique techniques described relates relating configured configure determining determine determined obtain obtained obtaining perform performed performing certain first second third based'.split())
# Preserve relation/negation words; avoid interpreting their removal as semantic cleaning.
protected={'no','not','without','before','after','above','below','between','during','within'}
english_stop=set(ENGLISH_STOP_WORDS)-protected
stop=english_stop|patent_stop
rules=[
 ('UE / user equipment',r'\buser equipments?\s*(?:\(\s*ues?\s*\))?|\bues?\b','user_equipment'),
 ('base station',r'\bbase stations?\b','base_station'),
 ('CSI / channel state information',r'\bchannel state information\s*(?:\(\s*csi\s*\))?|\bcsi\b','channel_state_information'),
 ('DRX / discontinuous reception',r'\bdiscontinuous reception\s*(?:\(\s*drx\s*\))?|\bdrx\b','drx'),
 ('HARQ / hybrid automatic repeat request',r'\bhybrid automatic repeat request\s*(?:\(\s*harq\s*\))?|\bharq\b','harq'),
 ('NR / new radio',r'\bnew radio\s*(?:\(\s*nr\s*\))?|\bnr\b','nr'),
 ('LTE / long term evolution',r'\blong[ -]term evolution\s*(?:\(\s*lte\s*\))?|\blte\b','lte'),
 ('Wi-Fi / WiFi',r'\bwi[ -]?fi\b','wifi'),
 ('reference signal',r'\breference signals?\b','reference_signal'),
 ('machine learning',r'\bmachine learning\b','machine_learning'),
 ('neural network',r'\bneural networks?\b','neural_network'),
]
plural={'channels':'channel','signals':'signal','resources':'resource','antennas':'antenna','stations':'station','beams':'beam','packets':'packet','networks':'network','frequencies':'frequency','transmissions':'transmission','receivers':'receiver','transmitters':'transmitter','slots':'slot','symbols':'symbol','subframes':'subframe','carriers':'carrier','communications':'communication','wirelessly':'wireless','transceivers':'transceiver','timers':'timer','messages':'message','measurements':'measurement'}
token_pattern=r'(?u)\b[a-z0-9][a-z0-9_]*\b'
def tokens(s):return [t for t in re.findall(token_pattern,s.lower()) if len(t)>1 and not t.isdigit()]
rule_counts=[]
working=text.str.lower()
for name,pattern,replacement in rules:
    rule_counts.append({'rule':name,'normalized_token':replacement,'matched_occurrences':int(working.str.count(pattern).sum())})
    working=working.str.replace(pattern,replacement,regex=True)
pre_stop=working.map(lambda s:[plural.get(t,t) for t in tokens(s)])
raw_tokens=text.map(tokens)
clean_tokens=pre_stop.map(lambda ts:[t for t in ts if t not in stop])
# Keep repeated technical tokens; occurrence counts carry information in sublinear TF.
clean_text=clean_tokens.map(' '.join)
removed=Counter(t for ts in pre_stop for t in ts if t in stop)
pd.DataFrame([{'term':t,'removed_occurrences':n,'category':'patent_boilerplate' if t in patent_stop else 'english_stopword'} for t,n in removed.most_common()]).to_csv(PUBLIC/'removed_terms.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(rule_counts).to_csv(PUBLIC/'normalization_rules.csv',index=False,encoding='utf-8-sig')
pd.DataFrame([{'source':k,'target':val} for k,val in plural.items()]).to_csv(PUBLIC/'plural_mapping.csv',index=False,encoding='utf-8-sig')
pd.DataFrame({'term':sorted(stop)}).to_csv(PUBLIC/'stopwords.csv',index=False,encoding='utf-8-sig')
base_params={'ngram_range':(1,2),'min_df':2,'max_df':1.0,'sublinear_tf':True,'norm':'l2','lowercase':False,'token_pattern':r'(?u)\b[a-z0-9][a-z0-9_]+\b'}
baseline=TfidfVectorizer(**base_params)
X0=baseline.fit_transform(raw_tokens.map(' '.join))
v=TfidfVectorizer(**base_params);X=v.fit_transform(clean_text);terms=v.get_feature_names_out()
save_npz(LOCAL/'step02_tfidf.npz',X)
(LOCAL/'step02_vocabulary.json').write_text(json.dumps(terms.tolist(),ensure_ascii=False),encoding='utf-8')
pd.DataFrame({'family_group':d.analysis_family_group,'Lens ID':d['Lens ID'],'Title':d.Title,'cleaned_text':clean_text,'raw_token_count':raw_tokens.map(len),'clean_token_count':clean_tokens.map(len),'tfidf_features':X.getnnz(axis=1)}).to_csv(LOCAL/'step02_cleaned_documents_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
def ranked(matrix,vectorizer):
    names=vectorizer.get_feature_names_out()
    return pd.DataFrame({'term':names,'mean_tfidf':np.asarray(matrix.mean(axis=0)).ravel(),'document_frequency':np.asarray((matrix>0).sum(axis=0)).ravel()}).sort_values(['mean_tfidf','term'],ascending=[False,True])
k0=ranked(X0,baseline);k=ranked(X,v)
k0.to_csv(PUBLIC/'keywords_before.csv',index=False,encoding='utf-8-sig');k.to_csv(PUBLIC/'keywords_after.csv',index=False,encoding='utf-8-sig')
technical=['user_equipment','base_station','sidelink','uplink','downlink','beam','reference_signal','channel_state_information','drx','harq','nr','lte','5g','4g','3gpp','mimo','ofdm','pdcch','pucch','pusch','prach','rach','wifi','bluetooth','positioning','security','machine_learning','neural_network']
vocab=set(terms)
checks=[]
for term in technical:
    df=int(clean_tokens.map(lambda ts:term in ts).sum())
    checks.append({'term':term,'documents_after_normalization':df,'in_tfidf_vocabulary':term in vocab,'reason':'preserved' if term in vocab else ('not_observed' if df==0 else 'outside_df_threshold')})
pd.DataFrame(checks).to_csv(PUBLIC/'technical_term_checks.csv',index=False,encoding='utf-8-sig')
norm=np.sqrt(X.multiply(X).sum(axis=1)).A1
empty=np.flatnonzero(X.getnnz(axis=1)==0)
# Audit of transformations, not a statistical validation of relevance or semantics.
assert len(d)==495 and d.analysis_family_group.nunique()==len(d)
assert np.isfinite(X.data).all() and (X.data>=0).all()
assert len(empty)==0 and np.allclose(norm,1,atol=1e-10)
assert not(set(terms)&stop)
assert all(term in vocab for term in ['sidelink','uplink','downlink','user_equipment','base_station','drx','nr'])
assert set(protected).isdisjoint(stop)
all_clean=Counter(t for ts in clean_tokens for t in ts)
lost_tokens=[{'term':t,'occurrences':n} for t,n in all_clean.most_common() if t not in vocab]
pd.DataFrame(lost_tokens).to_csv(PUBLIC/'tokens_outside_vocabulary.csv',index=False,encoding='utf-8-sig')
stats={'input_documents':len(d),'output_documents':X.shape[0],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'raw_token_occurrences':int(raw_tokens.map(len).sum()),'clean_token_occurrences':int(clean_tokens.map(len).sum()),'baseline_tfidf_features':X0.shape[1],'clean_tfidf_features':X.shape[1],'baseline_nonzero':int(X0.nnz),'clean_nonzero':int(X.nnz),'empty_documents':len(empty),'minimum_document_features':int(X.getnnz(axis=1).min()),'median_document_features':float(np.median(X.getnnz(axis=1))),'sidelink_title_documents':int(d.Title.str.contains('sidelink',case=False).sum()),'term_preservation_checks':checks,'matrix_checks':'finite, nonnegative, nonempty rows, row L2 norm=1, no configured stopwords in vocabulary','word_settings':base_params,'excluded_documents':0,'unobserved_or_df_filtered_terms':[x for x in checks if not x['in_tfidf_vocabulary']]}
(PUBLIC/'validation_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
fig,axs=plt.subplots(2,2,figsize=(16,11))
for ax,frame,title in [(axs[0,0],k0,'정제 전: 상투어·일반 용어 포함'),(axs[0,1],k,'정제 후: 주요 기술 용어')]:
    t=frame.head(15).iloc[::-1];ax.barh(t.term,t.mean_tfidf,color='#3578b5');ax.set_title(title);ax.set_xlabel('문헌 평균 TF-IDF (서로 다른 어휘 공간의 점수)')
axs[1,0].bar(['정제 전','정제 후'],[X0.shape[1],X.shape[1]],color=['#8798a8','#3578b5']);axs[1,0].set_title('단어·구문 특성 수 변화');axs[1,0].set_ylabel('TF-IDF 특성 수')
for i,n in enumerate([X0.shape[1],X.shape[1]]):axs[1,0].text(i,n,str(n),ha='center',va='bottom')
axs[1,0].set_ylim(0,max(X0.shape[1],X.shape[1])*1.15)
axs[1,1].hist(X.getnnz(axis=1),bins=25,color='#3578b5',edgecolor='white');axs[1,1].set_title(f'정제 후 문헌별 유효 특성 수 — 빈 문헌 {len(empty)}건');axs[1,1].set_xlabel('유효 TF-IDF 특성 수');axs[1,1].set_ylabel('문헌 수')
fig.suptitle('2단계 용어 정제·TF-IDF 검증 — 문헌을 제외하지 않고 입력 표현을 정리',fontsize=15)
fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(PUBLIC/'step02_validation.png',dpi=180);plt.close(fig)
print(json.dumps({key:val for key,val in stats.items() if key not in ['term_preservation_checks','word_settings']},ensure_ascii=True,indent=2))
print('TOP CLEAN TERMS',k.head(20).term.tolist())
