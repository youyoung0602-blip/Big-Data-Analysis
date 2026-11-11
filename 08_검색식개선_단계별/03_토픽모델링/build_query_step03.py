from pathlib import Path
import argparse,json,warnings,hashlib,itertools
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import NMF
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path.cwd();LOCAL=BASE/'query_refinement_steps';PUB=BASE/'Big-Data-Analysis'/'08_검색식개선_단계별'/'03_토픽모델링';PUB.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--topics',type=int,default=0);args=parser.parse_args()
X=load_npz(LOCAL/'step02_tfidf.npz');terms=np.array(json.loads((LOCAL/'step02_vocabulary.json').read_text(encoding='utf-8')))
docs=pd.read_csv(LOCAL/'step02_cleaned_documents_LOCAL_ONLY.csv').fillna('')
assert X.shape==(len(docs),len(terms)) and X.shape[0]==495 and X.shape[1]>100
binary=(X>0).astype(np.float64);n=X.shape[0];df=np.asarray(binary.sum(axis=0)).ravel()
def normalize(H,W):
    scale=np.maximum(np.linalg.norm(H,axis=1),1e-15)
    return H/scale[:,None],W*scale
def npmi(H):
    allpairs=[]
    for row in H:
        ids=row.argsort()[-8:]
        for a,b in itertools.combinations(ids,2):
            joint=float(binary[:,a].multiply(binary[:,b]).sum())/n
            if joint==0: val=-1.
            elif joint>=1:val=0.
            else:val=np.log(joint/((df[a]/n)*(df[b]/n)))/(-np.log(joint))
            allpairs.append(val)
    return float(np.mean(allpairs))
if args.topics==0:
    rows=[];previews={}
    with threadpool_limits(limits=2):
      for k in [6,8,10,12]:
        runs=[]
        for seed in [7,42,99]:
            model=NMF(n_components=k,init='random',random_state=seed,max_iter=1200,tol=1e-4,solver='cd')
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always',ConvergenceWarning)
                W=model.fit_transform(X)
            H,W=normalize(model.components_,W)
            runs.append((H,W,model.reconstruction_err_,model.n_iter_,any(issubclass(w.category,ConvergenceWarning) for w in caught)))
        main=runs[1];matches=[]
        for alt in [runs[0],runs[2]]:
            sim=main[0]@alt[0].T;ri,ci=linear_sum_assignment(-sim);matches.append(float(sim[ri,ci].mean()))
        H,W,err,iterations,warning=main
        topwords=[set(row.argsort()[-10:]) for row in H]
        distinct=len(set.union(*topwords))/(k*10)
        counts=np.bincount(W.argmax(axis=1),minlength=k)
        row={'topics':k,'reconstruction_error_relative':float(err/np.sqrt(X.multiply(X).sum())),'npmi_top8':npmi(H),'top10_word_diversity':distinct,'matched_topic_cosine_stability_mean':float(np.mean(matches)),'stability_min_run':float(min(matches)),'smallest_topic_documents':int(counts.min()),'largest_topic_documents':int(counts.max()),'main_iterations':iterations,'main_convergence_warning':warning,'any_run_convergence_warning':any(run[4] for run in runs)}
        rows.append(row)
        np.savez_compressed(LOCAL/f'step03_nmf_k{k}.npz',H=H,W=W)
        previews[str(k)]=[{'topic':i+1,'count':int(counts[i]),'terms':terms[h.argsort()[-12:][::-1]].tolist(),'local_representative_titles':docs.iloc[np.argsort(W[:,i])[::-1][:2]].Title.tolist()} for i,h in enumerate(H)]
        print(json.dumps(row,ensure_ascii=True),flush=True)
    pd.DataFrame(rows).to_csv(PUB/'topic_count_comparison.csv',index=False,encoding='utf-8-sig')
    (LOCAL/'step03_candidate_previews_LOCAL_ONLY.json').write_text(json.dumps(previews,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(previews,ensure_ascii=True,indent=2))
else:
    k=args.topics;model=np.load(LOCAL/f'step03_nmf_k{k}.npz');H=model['H'];W=model['W']
    mixture=W/np.maximum(W.sum(axis=1,keepdims=True),1e-15)
    assigned=mixture.argmax(axis=1);sortedweights=np.sort(mixture,axis=1)
    gap=sortedweights[:,-1]-sortedweights[:,-2]
    mixed=(mixture.max(axis=1)<.35)|(gap<.10)
    sim=X@H.T # H and X rows are both L2 normalized.
    counts=np.bincount(assigned,minlength=k);summaries=[];wordrows=[];examples=[]
    assignments=docs[['family_group','Lens ID','Title']].copy()
    assignments['topic']=assigned+1;assignments['top_weight']=mixture.max(axis=1);assignments['top_two_gap']=gap;assignments['mixed_topic_review']=mixed
    for i in range(k):
        assignments[f'topic_{i+1}_relative_weight']=mixture[:,i]
        ids=H[i].argsort()[-20:][::-1]
        within=np.where(assigned==i)[0]
        ordered=within[np.argsort(np.asarray(sim)[within,i])[::-1]]
        reps=[];seen_titles=set();seen_text=set()
        for j in ordered:
            title_key=str(docs.iloc[j].Title).strip().lower()
            text_key=str(docs.iloc[j].cleaned_text)
            if title_key in seen_titles or text_key in seen_text:continue
            reps.append(j);seen_titles.add(title_key);seen_text.add(text_key)
            if len(reps)==5:break
        summaries.append({'topic':i+1,'assigned_documents':int(counts[i]),'assigned_percent':float(counts[i]/n*100),'mixed_review_documents':int(mixed[within].sum()),'keywords':terms[ids[:12]].tolist()})
        for rank,j in enumerate(ids,1):wordrows.append({'topic':i+1,'rank':rank,'term':terms[j],'normalized_topic_coefficient':float(H[i,j]),'document_frequency':int(df[j])})
        for rank,j in enumerate(reps,1):examples.append({'topic':i+1,'rank':rank,'family_group':docs.iloc[j].family_group,'Lens ID':docs.iloc[j]['Lens ID'],'Title':docs.iloc[j].Title,'topic_cosine':float(np.asarray(sim)[j,i]),'top_weight':float(mixture[j,i]),'cleaned_text':docs.iloc[j].cleaned_text})
    assignments.to_csv(LOCAL/'step03_document_topics_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(examples).to_csv(LOCAL/'step03_representatives_LOCAL_ONLY.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(wordrows).to_csv(PUB/'topic_keywords.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([{key:val for key,val in s.items() if key!='keywords'} for s in summaries]).to_csv(PUB/'topic_counts.csv',index=False,encoding='utf-8-sig')
    similarities=H@H.T
    pd.DataFrame(similarities,index=[f'T{i+1:02}' for i in range(k)],columns=[f'T{i+1:02}' for i in range(k)]).rename_axis('topic').to_csv(PUB/'topic_similarities.csv',encoding='utf-8-sig')
    pairs=[{'topic_a':a+1,'topic_b':b+1,'cosine_similarity':float(similarities[a,b])} for a,b in itertools.combinations(range(k),2)]
    result={'documents':n,'features':X.shape[1],'selected_topics':k,'selected_seed':42,'init':'random','all_seeds':[7,42,99],'topics':summaries,'mixed_review_documents':int(mixed.sum()),'duplicate_clean_text_additional_records':int(docs.cleaned_text.duplicated().sum()),'highest_overlap_pairs':sorted(pairs,key=lambda r:-r['cosine_similarity'])[:5],'source_matrix_sha256':hashlib.sha256((LOCAL/'step02_tfidf.npz').read_bytes()).hexdigest(),'documents_excluded':0,'mixed_rule':'max relative weight <0.35 OR top two relative-weight gap <0.10; exploratory, not calibrated confidence'}
    (PUB/'topic_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    assert counts.sum()==n and np.isfinite(H).all() and np.isfinite(W).all()
    assert (H>=0).all() and (W>=0).all() and np.allclose(mixture.sum(axis=1),1)
    print(json.dumps(result,ensure_ascii=True,indent=2))
