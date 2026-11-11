from pathlib import Path
import hashlib,json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd();source=BASE/'qualcom1.csv'
out=BASE/'query_refinement_steps';out.mkdir(exist_ok=True)
public=BASE/'Big-Data-Analysis'/'08_검색식개선_단계별';step=public/'01_데이터점검';step.mkdir(parents=True,exist_ok=True)
d=pd.read_csv(source).fillna('');parent=list(range(len(d)));seen={}
def root(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
for i,row in d.iterrows():
    for m in set(str(row['Simple Family Members']).split(';;')+[str(row['Lens ID'])]):
        if not m:continue
        if m in seen:parent[root(i)]=root(seen[m])
        else:seen[m]=i
d['analysis_family_group']=[root(i) for i in range(len(d))]
d['abstract_length']=d.Abstract.str.len()
r=d.sort_values(['abstract_length','Lens ID'],ascending=[False,True]).drop_duplicates('analysis_family_group').sort_values('analysis_family_group').copy()
r['family_earliest_priority_date']=r.analysis_family_group.map(d.groupby('analysis_family_group')['Earliest Priority Date'].min())
union=d.groupby('analysis_family_group')['CPC Classifications'].apply(lambda s:';;'.join(sorted(set(code for item in s for code in item.split(';;') if code))))
r['family_cpc_union']=r.analysis_family_group.map(union)
r.drop(columns='abstract_length').to_csv(out/'step01_family_representatives_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
years=pd.DataFrame({'input_documents':d['Publication Year'].value_counts(),'representative_documents':r['Publication Year'].value_counts()}).fillna(0).astype(int).sort_index();years.index.name='publication_year';years.to_csv(step/'publication_year_counts.csv',encoding='utf-8-sig')
stats={'input_filename':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'input_documents':len(d),'family_groups':len(r),'repeated_family_documents':len(d)-len(r),'missing_abstracts':int((d.Abstract=='').sum()),'h04w_documents':int(d['CPC Classifications'].str.contains('H04W').sum()),'representative_rule':'Longest available abstract, Lens ID ascending for ties; not an assessment of patent value.','lens_screenshot_counts_not_requeried':{'records':41476,'simple_families':21900,'jurisdiction_filter':'United States'},'analysis_scope':'Exploratory subset only. No claim of representativeness for full Lens results.'}
(step/'audit_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams['font.family']='Malgun Gothic';plt.rcParams['axes.unicode_minus']=False
fig,axs=plt.subplots(1,2,figsize=(14,5))
axs[0].bar(['입력 문헌','패밀리 대표','패밀리 내 추가 문헌'],[len(d),len(r),len(d)-len(r)],color=['#8292a2','#3578b5','#db9453']);axs[0].set_title('패밀리 중복을 줄이는 단계 — 주제 제외 아님');axs[0].set_ylabel('문헌 수')
for i,n in enumerate([len(d),len(r),len(d)-len(r)]):axs[0].text(i,n+10,str(n),ha='center')
axs[0].set_ylim(0,1150)
years.plot.bar(ax=axs[1],color=['#8292a2','#3578b5']);axs[1].legend(['입력 문헌','선택 대표 문헌']);axs[1].set_title('파일 내 공개연도 분포 — 전체 검색 결과의 추세 아님');axs[1].set_xlabel('공개연도');axs[1].set_ylabel('문헌 수')
fig.tight_layout();fig.savefig(step/'step01_data_audit.png',dpi=180);plt.close(fig)
report=f'''# 1단계 — 데이터 범위와 패밀리 중복 점검

## 이번 단계의 목적

토픽모델링 전에 어떤 자료를 분석하는지 확인하고, 같은 발명의 여러 문헌이 특정 주제의 비중을 부풀리지 않도록 중복을 줄인다. **이 단계에서 관련 없는 기술을 판정하거나 검색식을 변경하지는 않았다.**

## 전체 목표와 현재 파일의 차이

사용자 제공 Lens 화면에는 미국 필터에서 문헌 41,476건, Simple Families 21,900개가 표시돼 있다. 이는 화면에서 확인한 값이며 현재 직접 재검색한 수치는 아니다. 목표는 대표 5,000개를 추출하는 것이 아니라 **연구 범위를 반영한 수정 검색식으로 Lens의 Simple Families 결과 자체를 5,000개 이하로 줄이는 것**이다.

현재 입력 qualcom1.csv에는 1,000개 문헌만 있다. 이 파일의 분석은 검색식 후보를 찾는 탐색에 사용할 수 있지만 전체 21,900개 패밀리를 대표한다고 가정하지 않는다. 마지막 건수 확인은 반드시 Lens에서 해야 한다.

## 점검 결과

| 항목 | 결과 |
|---|---:|
| 입력 문헌 | {len(d):,}건 |
| H04W 포함 문헌 | {stats['h04w_documents']:,}건 |
| 초록 누락 | {stats['missing_abstracts']}건 |
| 패밀리 연결 그룹 | {len(r):,}개 |
| 그룹당 한 문헌만 남기면 빠지는 추가 문헌 | {len(d)-len(r):,}건 |

![데이터 범위와 패밀리 중복 점검](./step01_data_audit.png)

## 어떻게 묶고 대표를 골랐는가

1. 각 행의 Lens ID와 Simple Family Members 목록을 연결한다.
2. 같은 멤버 ID를 공유하는 행들을 한 연결 그룹으로 묶는다. 가족 정보가 완전하지 않으면 실제 Lens 패밀리 구분과 차이가 있을 수 있다.
3. 그룹 안에서 초록이 가장 긴 문헌 하나를 대표로 선택한다. 길이가 같으면 Lens ID 오름차순으로 정한다. 이는 모델 입력 텍스트 확보를 위한 규칙이지 중요 특허 선정이 아니다.
4. 그룹에 속한 문헌들의 CPC는 합집합으로, 최초 우선일은 최솟값으로 별도 보존한다. 후속 텍스트 분석에는 선택한 대표 문헌의 제목·초록을 사용한다.

1,000개가 495개로 줄어든 것은 ‘505개가 노이즈여서’가 아니라 **같은 패밀리의 반복 문헌을 한 번만 분석하려는 처리**다. 분할·계속출원 등 서로 다른 simple family의 유사 문헌까지 모두 제거한 것은 아니다.

## 이번 단계의 산출물

- 로컬 `query_refinement_steps/step01_family_representatives_LOCAL_ONLY.csv`: 다음 단계에 사용할 대표 문헌 495개. 원본은 변경하지 않았다.
- [공개연도별 집계](./publication_year_counts.csv): 선택 대표 문헌의 공개연도 분포는 발명의 최초 발생연도나 전체 포트폴리오의 추세와 다르다.
- [점검 수치와 입력 해시](./audit_summary.json)
- [재현 코드](./build_query_step01.py)

문헌별 제목·초록·식별자는 신규 GitHub 업로드 대상에서 제외했다. 공개연도·초록 길이 기준 선택과 표본 추출 방식에 따른 편향은 남는다.

## 다음 단계 — 용어 정제와 TF-IDF

495개 대표 문헌의 제목·초록에서 특허 상투어, 약어·동의어, 단복수를 정리한다. 제거·통합 전후 예시와 단어 수 변화를 보여주고, 다음 토픽모델링에 쓸 TF-IDF 행렬을 만든다. **TF-IDF 점수가 낮다는 이유만으로 문서를 제외하지 않는다.**
'''
(step/'README.md').write_text(report,encoding='utf-8')
(public/'README.md').write_text('''# 검색식 개선 — 단계별 작업

목표: 수정 검색식으로 Lens의 Simple Families 검색 결과를 5,000개 이하로 좁힌다. 전체에서 대표 문헌 5,000개를 뽑는 표본 선정과 구분한다.

| 단계 | 목적 | 상태 |
|---|---|---|
| [01 데이터 점검](./01_데이터점검/) | qualcom1.csv 범위 확인·패밀리 중복 정리 | 완료 |
| 02 용어 정제·TF-IDF | 불용어·표기 통합과 기술 용어 표현 | 다음 단계 |
| 03 토픽모델링 | 문헌에 섞인 기술 주제와 대표 용어 확인 | 예정 |
| 04 포함·제외 주제 검토 | 연구 목적에 맞는 핵심·주변 기술 구분 | 예정 |
| 05 검색식 후보 작성 | 핵심어·세부 CPC와 조건 조합 | 예정 |
| 06 Lens 실행 검증 | 패밀리 수와 관련 문헌 누락 확인 | 예정 |

각 단계의 결과를 확인한 뒤 다음 단계로 이어간다. 지금까지 노이즈 문서를 확정해 삭제하거나 5,000개 이하로 줄였다는 의미는 아니다. 현재 파일은 전체 검색 결과 중 1,000개 문헌만 포함하므로 검색식 후보의 전체 결과 수는 Lens에서 확인해야 한다.
''',encoding='utf-8')
print(json.dumps(stats,ensure_ascii=True,indent=2))
