from pathlib import Path
import re,json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

B=Path.cwd();L=B/'query_refinement_steps'
P=B/'Big-Data-Analysis'/'08_검색식개선_단계별'/'04_연구범위검토';P.mkdir(parents=True,exist_ok=True)
r=pd.read_csv(L/'step01_family_representatives_LOCAL_ONLY.csv').fillna('')
t=pd.read_csv(L/'step03_document_topics_LOCAL_ONLY.csv').fillna('')
r=r.merge(t[['family_group','topic']],left_on='analysis_family_group',right_on='family_group',how='left',validate='one_to_one')
assert len(r)==495 and r.topic.notna().all()
text=(r.Title+' '+r.Abstract).str.lower()
def hit(pattern):return text.str.contains(pattern,regex=True)
sl=hit(r'\bsidelink\b|\bside[ -]link\b|\bpc5\b')
drx=hit(r'\bdrx\b|\bdiscontinuous reception\b')
resource=hit(r'\bresources?\b|\bschedul\w*\b|\bgrant\w*\b|\bpreempt\w*\b')
nr=hit(r'\bnew radio\b|\bnr\b|\b5g\b|\bfifth generation\b')
beam=hit(r'\bbeam\w*\b')&hit(r'\bselect\w*\b|\btrack\w*\b|\bmanagement\b|\bsweep\w*\b|\brefin\w*\b|\bfailure\b|\btrain\w*\b')
rach=hit(r'\brandom access\b|\brach\b|\bprach\b')
two=hit(r'\b(?:two|2)[ -]step\b')
relay=hit(r'\brelay\w*\b')
cases=[('A0','사이드링크 전반',sl),('A1','사이드링크 + DRX',sl&drx),('A2','사이드링크 + 자원·스케줄링',sl&resource),('A3','사이드링크 + DRX + 자원',sl&drx&resource),('A4','A3 + NR/5G 명시',sl&drx&resource&nr),('A5','사이드링크 + (DRX 또는 자원)',sl&(drx|resource)),('A6','사이드링크 + (DRX·자원·중계 중 하나)',sl&(drx|resource|relay)),('B','빔 관리·선택·추적',beam),('C0','랜덤 액세스·RACH',rach),('C1','RACH + 2단계 접속',rach&two)]
rows=[];bytopic=[]
local=r[['Lens ID','Title','URL','analysis_family_group','topic']].copy()
for key,label,m in cases:
    rows.append({'candidate':key,'scope':label,'sample_matches':int(m.sum()),'sample_not_matched':int((~m).sum()),'sample_match_percent':float(m.mean()*100),'lens_family_count':'not_measured'})
    local[key]=m
    for i in range(1,9):
        group=r.topic.eq(i)
        bytopic.append({'candidate':key,'topic':i,'topic_documents':int(group.sum()),'matched_documents':int((m&group).sum()),'not_matched_documents':int((~m&group).sum())})
pd.DataFrame(rows).to_csv(P/'candidate_scope_counts.csv',index=False,encoding='utf-8-sig')
pd.DataFrame(bytopic).to_csv(P/'candidate_topic_cross_table.csv',index=False,encoding='utf-8-sig')
local.to_csv(L/'step04_scope_matches_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
groups=[('H04W76/28','DRX·DTX'),('H04W52/02','절전'),('H04W72/40','D2D·사이드링크 자원 관리'),('H04W72/25','사이드링크 자원 관리 신호'),('H04W88/04','단말 중계'),('H04W16/28','빔 조향'),('H04B7/0695','빔 선택'),('H04W74/08','비예약·경쟁 접속')]
cpcrows=[]
for code,description in groups:
    doc=r['CPC Classifications'].map(lambda s:any(x.startswith(code) for x in str(s).split(';;')))
    fam=r.family_cpc_union.map(lambda s:any(x.startswith(code) for x in str(s).split(';;')))
    cpcrows.append({'CPC_prefix':code,'description':description,'representative_document_matches':int(doc.sum()),'family_member_union_matches':int(fam.sum())})
pd.DataFrame(cpcrows).to_csv(P/'cpc_scope_evidence.csv',index=False,encoding='utf-8-sig')
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
fig,axs=plt.subplots(1,2,figsize=(16,7))
labels=[x[0]+' '+x[1] for x in cases];vals=[row['sample_matches'] for row in rows]
axs[0].barh(labels[::-1],vals[::-1],color=['#3578b5' if x!='A6' else '#d9914d' for x,_,_ in cases][::-1]);axs[0].set_xlabel('495개 대표 문헌 중 표현 조건 일치 수');axs[0].set_title('연구 범위를 좁히면 표본에서 무엇이 남는가')
for i,val in enumerate(vals[::-1]):axs[0].text(val+1,i,str(val),va='center')
axs[0].set_xlim(0,max(vals)*1.12)
tab=pd.DataFrame(bytopic).pivot(index='candidate',columns='topic',values='matched_documents').reindex([x[0] for x in cases]);im=axs[1].imshow(tab,cmap='Blues',aspect='auto')
axs[1].set_yticks(range(len(cases)),tab.index);axs[1].set_xticks(range(8),[f'T{i}' for i in range(1,9)]);axs[1].set_title('각 조건에서 남는 문헌의 대표 토픽')
for i in range(len(cases)):
 for j in range(8):axs[1].text(j,i,str(tab.iloc[i,j]),ha='center',va='center',fontsize=9,color='white' if tab.iloc[i,j]>tab.to_numpy().max()*.55 else 'black')
fig.colorbar(im,ax=axs[1],label='문헌 수');fig.suptitle('표본 내 조건 비교 — Lens 전체 패밀리 수·정확도 추정이 아님');fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(P/'step04_scope_comparison.png',dpi=180);plt.close(fig)
result={'documents':495,'scope_choice':'user_selected_sidelink_resource_allocation_drx_relay','selected_candidate':'A6','recommended_research_focus':'Sidelink DRX and resource allocation interaction, with relay as a related subtopic','candidate_counts':rows,'cpc_evidence':cpcrows,'keywords_proxy_only':True,'lens_counts_not_queried':True,'documents_deleted':0}
(P/'scope_review_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
assert (sl&drx&resource).sum()<=(sl&drx).sum()<=sl.sum()
assert (sl&drx&resource&nr).sum()<=(sl&drx&resource).sum()
print(json.dumps(result,ensure_ascii=True,indent=2))
