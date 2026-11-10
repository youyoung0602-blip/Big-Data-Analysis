from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path('qualcomm_analysis')
raw=pd.read_csv('lens-export.csv').fillna('')
parent=list(range(len(raw))); seen={}
def root(i):
    while parent[i]!=i:
        parent[i]=parent[parent[i]]; i=parent[i]
    return i
for i,row in raw.iterrows():
    for m in set(str(row['Simple Family Members']).split(';;')+[str(row['Lens ID'])]):
        if not m: continue
        if m in seen: parent[root(i)]=root(seen[m])
        else: seen[m]=i
raw['family_group']=[root(i) for i in range(len(raw))]
raw['priority_date']=pd.to_datetime(raw['Earliest Priority Date'],errors='coerce')
dates=raw.groupby('family_group').priority_date.min()
r=pd.read_csv(OUT/'family_topics.csv')
r['priority_date']=r.family_group.map(dates)
r['priority_year']=r.priority_date.dt.year
names={0:'무선통신',4:'무선통신',1:'비디오 코딩',2:'컴퓨터 비전',3:'터치 센싱',5:'음향·MEMS·회로',6:'AI·관련 연산',7:'오디오'}
order=['무선통신','비디오 코딩','컴퓨터 비전','AI·관련 연산','음향·MEMS·회로','터치 센싱','오디오']
r['technology']=r.topic.map(names)
counts=pd.crosstab(r.priority_year,r.technology).reindex(columns=order,fill_value=0)
counts=counts.reindex(range(int(counts.index.min()),int(counts.index.max())+1),fill_value=0)
counts.index.name='priority_year'
total=counts.sum(axis=1)
shares=counts.div(total.replace(0,np.nan),axis=0)*100
counts.to_csv(OUT/'yearly_technology_counts.csv',encoding='utf-8-sig')
shares.to_csv(OUT/'yearly_technology_shares.csv',encoding='utf-8-sig')
r[['family_group','Lens ID','Title','priority_date','priority_year','technology','URL']].to_csv(OUT/'family_priority_years.csv',index=False,encoding='utf-8-sig')
assert counts.to_numpy().sum()==658
assert np.allclose(shares.loc[total>0].sum(axis=1),100)
plt.rcParams['font.family']='Malgun Gothic'; plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(2,1,figsize=(15,11),sharex=True)
c=counts.loc[2010:2024]; s=shares.loc[2010:2024]
colors=plt.get_cmap('tab10')(np.arange(7))
bottom=np.zeros(len(c))
for name,color in zip(order,colors):
    axes[0].bar(c.index,c[name],bottom=bottom,label=name,color=color)
    bottom+=c[name].to_numpy()
for year,n in c.sum(axis=1).items(): axes[0].text(year,n+2,str(n),ha='center',fontsize=9)
axes[0].set_ylabel('패밀리 대표 문헌 수'); axes[0].set_ylim(0,270)
axes[0].set_title('연도별 기술 구성: 패밀리 최초 우선연도 기준\n2019년 표본 집중, 2024년 관측 4건에 유의')
bottom=np.zeros(len(s))
for name,color in zip(order,colors):
    axes[1].bar(s.index,s[name],bottom=bottom,label=name,color=color)
    bottom+=s[name].fillna(0).to_numpy()
axes[1].set_ylabel('해당 연도 표본 내 비중 (%)'); axes[1].set_ylim(0,100)
axes[1].set_xlabel('최초 우선연도 (2024년은 소표본·우측 절단에 유의)')
axes[1].set_xticks(c.index)
axes[0].legend(ncol=4,loc='upper right',fontsize=10)
for ax in axes:
    ax.axvspan(2023.5,2024.5,color='black',alpha=.08)
    ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(OUT/'yearly_technology_trends.png',dpi=180); plt.close(fig)

report='''# 퀄컴 연도별 기술 추세 분석

이 표본에서는 2014~2019년 무선통신 중심 구성이 두드러지고, 2020년 이후에는 비전·AI·음향/MEMS 관련 기술의 비중이 높아진다. **이는 표본 구성의 변화이며 퀄컴 전체 R&D가 통신에서 AI로 이동했다는 증거는 아니다.**

## 기준과 범위

- 동일한 분석 대상 658개 패밀리 그룹, 기존 NMF 주제 배정을 유지했다. 비교를 위해 단말·기지국과 무선 채널·전송의 두 주제는 무선통신으로 합쳤다.
- 각 패밀리에 속한 원본 문헌들의 Earliest Priority Date 중 최솟값을 사용했다. 따라서 국가별 공개·등록 시차를 줄이고 발명의 초기 시점에 가깝게 비교한다. 모든 문헌을 확보한 것은 아니므로 실제 법적 우선권 관계를 재검증한 결과는 아니다.
- 그래프는 2010~2024년을 표시하고 CSV에는 2003~2024년을 포함했다. 2010년 이전은 총 24개 그룹으로 적다. 날짜를 확인할 수 없는 그룹은 없다.
- 건수와 연도 내 비중을 함께 확인했다. 비중은 각 연도 해당 기술 건수 ÷ 그 연도 전체 분석 대상 건수다.
- 2024년은 4개 그룹뿐이고 원본의 가장 늦은 최초 우선일도 2024-03-06이다. 소표본·추출 범위·공개 시차에 따른 우측 절단 가능성이 있어 완결 연도의 추세로 해석하지 않는다. 2025년 우선권 그룹은 이 파일에 없으며 0건의 R&D를 뜻하지 않는다.

## 연도별 그래프

![연도별 기술 건수와 표본 내 비중](./yearly_technology_trends.png)

위쪽은 건수, 아래쪽은 연도별 비중이다. 2019년 표본 집중이 건수 그래프에서 뚜렷하다. 비중으로 바꾸어도 검색식과 추출 방식에 따른 편향은 제거되지 않는다.

## 연도별 주요 변화

| 최초 우선연도 | 전체 그룹 수 | 가장 많은 기술 (건수·비중) | AI·관련 연산 비중 | 컴퓨터 비전 비중 |
|---|---:|---|---:|---:|
'''
for year in range(2010,2025):
    row=counts.loc[year]; n=int(row.sum()); top=row.idxmax()
    report+=f'| {year} | {n} | {top} {int(row[top])}건 ({shares.loc[year,top]:.1f}%) | {shares.loc[year,"AI·관련 연산"]:.1f}% | {shares.loc[year,"컴퓨터 비전"]:.1f}% |\n'
report+='''
2018년은 무선통신 4건(33.3%), 컴퓨터 비전 3건(25.0%)이다.

### 2011~2013년: 기술 구성이 비교적 분산

2011년은 AI·관련 연산이 10/36건(27.8%), 2012년은 12/46건(26.1%)이다. 2013년은 무선통신 7건, 비전 8건, 오디오 6건, 터치 5건 등 여러 기술이 섞인다. AI가 최근에 처음 등장했다고 볼 수 없다. 기존 AI 주제에는 신경망 외 관련 연산 문헌도 포함된다.

### 2014~2019년: 무선통신 중심 구성이 뚜렷

무선통신은 2014년 23/47건(48.9%), 2015년 18/38건(47.4%), 2016년 23/35건(65.7%), 2017년 15/24건(62.5%)이다. 2018년은 총 12건으로 적고 통신은 4건(33.3%)이다.

2019년은 240건 중 무선통신 170건(70.8%), 비디오 코딩 31건(12.9%)이다. **2019년 한 해가 전체 658건의 36.5%를 차지한다.** 전체 분석에서 통신 비중이 큰 데에는 이 연도의 집중도 영향을 준다. 단순히 통신 연구개발이 급증했다고 단정할 수 없다.

### 2020~2022년: 비전·AI·음향/MEMS 비중 상승

2020년은 비전 6건, 음향·MEMS·회로 6건, AI·관련 연산 5건이다. 2021년은 음향·MEMS·회로 10/20건(50.0%), 2022년은 비전 9/21건(42.9%), AI·관련 연산 7/21건(33.3%)이다. 최근 표본은 통신 일변도보다 인식·학습·센싱 기술 쪽으로 구성 비중이 이동한다.

### 2023년: AI·비전이 대부분

2023년은 AI·관련 연산 16/27건(59.3%), 비전 9/27건(33.3%)으로 두 분야가 92.6%다. AI 주제는 2020년 5건, 2021년 4건, 2022년 7건, 2023년 16건으로 관측된다. 이는 이 표본에서 최근 AI 관련 문헌의 존재감이 커졌다는 근거다. 다만 같은 기간 통신 문헌의 표본 포착이 극히 적어 회사 전체의 기술 전환으로 일반화할 수 없다.

2024년은 AI 3건, 비전 1건이다. 단 4건이므로 전년 대비 성장률이나 추세 지속의 근거로 사용하지 않았다.

## 해석상 유의점

특허 검색식, 정렬 순서, 1,000건 추출 제한 여부가 확인되지 않았다. 2019년 집중과 최근 통신 문헌의 희소성이 실제 전략 변화인지 검색 표본 편향인지 분리할 수 없다. 최근 문헌은 공개 지연으로 적게 포착될 수도 있다. 특정 연도 0건은 기술 활동의 중단을 의미하지 않는다.

연도별로 TF-IDF/NMF를 다시 학습하지 않고 동일한 모델의 주제를 유지해 비교했다. 모델의 자동 분류 오차도 그대로 남는다. 시계열 회귀나 성장률 추정은 표본의 불균형이 크고 관측 연도별 규모가 작아 수행하지 않았다.

## 데이터

- [연도별 기술 건수 CSV](./yearly_technology_counts.csv)
- [연도별 기술 비중 CSV](./yearly_technology_shares.csv)
- [패밀리별 우선일·기술 분류 CSV](./family_priority_years.csv)
- [분석 코드](./qualcomm_trends.py): 원본 lens-export.csv 및 기존 qualcomm_analysis/family_topics.csv가 있는 Downloads에서 실행.
'''
(OUT/'퀄컴_연도별_기술추세.md').write_text(report,encoding='utf-8')
print(counts.to_string())
print('Total:',int(total.sum()),'Missing dates:',int(r.priority_year.isna().sum()))
