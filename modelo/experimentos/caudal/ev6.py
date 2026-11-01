import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q26/ev5.py').read().split("rng=np.random")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/app/serie.json'))
S1=pd.DataFrame(J['s1']); S1['f']=pd.to_datetime(S1.f); S1=S1.groupby('f').mean()
rng=np.random.default_rng(3)
for nm in ['Olaya','Olaya → Sitio Presa (San Andrés, Ituango, Espíritu Santo…)','La Virginia (Cauca alto)']:
    q=inc[nm]['2019-02-01':'2026-10-15']; pk,thr=picks(q); valid=q.dropna().index
    for lab,s in [('radar aguas arriba',S1.a),('radar aguas abajo',S1.b),('radar total',S1.t)]:
        for win in [((1,24),(0,12)),((1,24),(12,36))]:
            e=comp(s,pk,win); base=[]
            for _ in range(400):
                rd=[pd.Timestamp(year=int(rng.choice(sorted(set(valid.year)))),month=t.month,day=min(t.day,28)) for t in pk]; rd=[x for x in rd if x in valid]
                b=comp(s,rd,win); 
                if len(b): base.append(np.median(b))
            base=np.array(base); print(nm[:20],lab,win[1],dict(n=len(e),evento=round(float(np.median(e)),2),azar=round(float(np.median(base)),2),p=round(float((base>=np.median(e)).mean()),3)),flush=True)
