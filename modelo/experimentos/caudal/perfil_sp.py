import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q26/ev5.py').read().split("rng=np.random")[0])
q=X.sitiopresa['2021-10-01':'2026-08-31']; pk,thr=picks(q)
rng=np.random.default_rng(5); valid=q.dropna().index
def prof(days,s):
    M=[]
    for t in days:
        pre=s[t-pd.Timedelta(days=28):t-pd.Timedelta(days=1)].mean()
        if not pre>0: continue
        M.append([s[t+pd.Timedelta(days=7*k):t+pd.Timedelta(days=7*k+6)].mean()/pre for k in range(8)])
    return np.nanmedian(np.array(M),axis=0),len(M)
out={}
for lab,s in [('MF m³/día activo',d.mfrate),('MF total diario',d.mf_tot),('MA m³/día activo',d.marate)]:
    e,n=prof(pk,s); B=[]
    for _ in range(300):
        rd=[pd.Timestamp(year=int(rng.choice(sorted(set(valid.year)))),month=t.month,day=min(t.day,28)) for t in pk]; rd=[x for x in rd if x in valid]
        B.append(prof(rd,s)[0])
    B=np.array(B); base=np.nanmedian(B,axis=0); p=[(B[:,k]>=e[k]).mean() for k in range(8)]
    out[lab]=dict(n=n,evento=[round(x,2) for x in e],azar=[round(x,2) for x in base],p=[round(x,3) for x in p])
    print(lab,n,'\n evento',out[lab]['evento'],'\n azar  ',out[lab]['azar'],'\n p     ',out[lab]['p'])
# volumen adicional típico de MF en 4 semanas
ex=[]
for t in pk:
    pre=d.mf_tot[t-pd.Timedelta(days=28):t-pd.Timedelta(days=1)].sum(); post=d.mf_tot[t:t+pd.Timedelta(days=27)].sum(); ex.append(post-pre)
print('umbral',round(thr),'eventos',len(pk),'MF 4 sem después − 4 sem antes: mediana',round(np.median(ex)),'P25–P75',np.percentile(ex,[25,75]).round())
print([str(t.date()) for t in pk])
json.dump(dict(umbral_sitiopresa=round(float(thr)),eventos=[str(t.date()) for t in pk],perfil=out,extra_mf_4sem_mediana=round(float(np.median(ex))),extra_p25_p75=np.percentile(ex,[25,75]).round().tolist()),open('/home/claude/work/q26/perfil_sp.json','w'),indent=1,ensure_ascii=False)
