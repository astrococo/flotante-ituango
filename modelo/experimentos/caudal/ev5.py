import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
X=pd.read_csv('/home/claude/work/q26/caudales_cuenca.csv',index_col=0,parse_dates=True)
inc={'La Virginia (Cauca alto)':X.virginia,
     'La Virginia → La Pintada (Risaralda, Caldas)':X.pintada-X.virginia.shift(1),
     'La Pintada → Bolombolo':X.bolombolo-X.pintada.shift(1),
     'Bolombolo → Olaya':X.olaya-X.bolombolo,
     'Olaya → Sitio Presa (San Andrés, Ituango, Espíritu Santo…)':X.sitiopresa-X.olaya,
     'Olaya':X.olaya}
d['mfrate']=d.mf_tot.where(d.mf_tot>0); d['marate']=d.ma_tot.where(d.ma_tot>0)
def picks(q,qq=0.9,sep=30):
    q=q.dropna(); thr=q.quantile(qq); pk=[]
    for t,v in q[q>thr].sort_values(ascending=False).items():
        if all(abs((t-p).days)>=sep for p in pk): pk.append(t)
    return sorted(pk),thr
def comp(series,days,win):
    out=[]
    for t in days:
        a=series[t-pd.Timedelta(days=win[0][1]):t-pd.Timedelta(days=win[0][0])]; b=series[t+pd.Timedelta(days=win[1][0]):t+pd.Timedelta(days=win[1][1])]
        if a.notna().sum()<3 or b.notna().sum()<3 or a.mean()<=0: continue
        out.append(b.mean()/a.mean())
    return np.array(out)
rng=np.random.default_rng(2); res={}
for per,(i0,i1) in {'2019-2026':('2019-08-15','2026-08-31'),'oct2021-2026':('2021-10-01','2026-08-31')}.items():
    for nm,q in inc.items():
        q=q[i0:i1]
        if q.notna().sum()<300: continue
        pk,thr=picks(q); valid=q.dropna().index
        r={'umbral':round(float(thr)),'eventos':len(pk)}
        for lab,s in [('MF m³/día activo 0–4 sem',d.mfrate),('MA m³/día activo 0–4 sem',d.marate),('MF total 0–4 sem',d.mf_tot)]:
            e=comp(s,pk,((1,28),(0,27))); base=[]
            for _ in range(400):
                rd=[]
                for t in pk:
                    y=int(rng.choice(sorted(set(valid.year)))); x=pd.Timestamp(year=y,month=t.month,day=min(t.day,28))
                    if x in valid: rd.append(x)
                b=comp(s,rd,((1,28),(0,27)))
                if len(b): base.append(np.median(b))
            base=np.array(base); r[lab]=dict(evento=round(float(np.median(e)),2),azar=round(float(np.median(base)),2),p=round(float((base>=np.median(e)).mean()),3),n=len(e))
        res[f'{per} | {nm}']=r; print(per,'|',nm,r,flush=True)
json.dump(res,open('/home/claude/work/q26/subcuencas.json','w'),indent=1,ensure_ascii=False)
