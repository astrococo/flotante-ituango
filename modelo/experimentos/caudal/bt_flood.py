import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
P=json.load(open('/home/claude/work/params_v21.json'))['mf_tot']; ah=P['a_h']
B=pd.read_pickle('/home/claude/work/exp26/B_mf_tot.pkl')
B['nc']=0.5*(B.h.map(lambda h:ah[h-1])*B.ew+(1-B.h.map(lambda h:ah[h-1]))*B.ltm)+0.5*B.ltm
B['ts']=B.o+pd.to_timedelta((B.h-1)*7+1,unit='D')   # inicio de la semana objetivo
q=d.olaya  # completo 2019-2026 (Sitio Presa obs ≈ 1,049·Olaya+30)
out={}
for thr in [1600,1750,1900,2100]:
    for win in [28,42]:
        # creciente conocida al origen: pico ≥ thr entre (inicio objetivo − win) y el origen
        def flag(r):
            a=max(r.ts-pd.Timedelta(days=win),pd.Timestamp('2019-07-01')); b=r.o
            return bool((q[a:b]>=thr).any()) if a<=b else False
        B['fl']=[flag(r) for r in B.itertuples()]
        res={}
        for yr in range(2022,2027):
            tr=B[(B.o.dt.year!=yr)&B.fl]; te=B[B.o.dt.year==yr]
            k=float(np.clip(np.median(tr.y/tr.nc),1,2)) if len(tr)>10 else 1
            te_f=te.nc*np.where(te.fl,k,1)
            res[yr]=dict(k=round(k,2),n_fl=int(te.fl.sum()),skill_base=round(1-rm(te.nc,te.y)/rm(te.ltm,te.y),3),skill_fl=round(1-rm(te_f,te.y)/rm(te.ltm,te.y),3))
        g=B[B.o>='2022-01-01']
        allk=[]; f=[]
        for yr in range(2022,2027):
            tr=B[(B.o.dt.year!=yr)&B.fl]; k=float(np.clip(np.median(tr.y/tr.nc),1,2)); te=g[g.o.dt.year==yr]; f.append(te.nc*np.where(te.fl,k,1))
        f=pd.concat(f)
        out[f'{thr}_{win}']=dict(rmse_base=round(rm(g.nc,g.y)),rmse_fl=round(rm(f,g.y)),frac=round(float(g.fl.mean()),3),por_año=res)
        print(thr,win,out[f'{thr}_{win}']['rmse_base'],'->',out[f'{thr}_{win}']['rmse_fl'],'frac',out[f'{thr}_{win}']['frac'],{y:(v['k'],v['skill_base'],v['skill_fl']) for y,v in res.items()})
json.dump(out,open('/home/claude/work/q26/bt_flood.json','w'),indent=1)
