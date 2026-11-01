import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
P=json.load(open('/home/claude/work/params_v21.json'))['mf_tot']; ah=P['a_h']
B=pd.read_pickle('/home/claude/work/exp26/B_mf_tot.pkl')
B['nc']=0.5*(B.h.map(lambda h:ah[h-1])*B.ew+(1-B.h.map(lambda h:ah[h-1]))*B.ltm)+0.5*B.ltm
B['ts']=B.o+pd.to_timedelta((B.h-1)*7+1,unit='D')
q=d.olaya
out={}
for thr in [1600,1750,2000]:
    # picos (máximo local diario ≥ thr, separados ≥ 14 d)
    pk=[]; 
    for t,v in q[q>=thr].sort_values(ascending=False).items():
        if all(abs((t-p).days)>=14 for p in pk): pk.append(t)
    pk=pd.DatetimeIndex(sorted(pk))
    def kk(r):
        c=pk[(pk<=r.o)]
        if not len(c): return -1
        k=(r.ts-c[-1]).days//7
        return int(k) if 0<=k<=7 else -1
    B['k']=[kk(r) for r in B.itertuples()]
    for desde in ['2019-07-01','2021-10-01']:
        f=[]
        for yr in range(2022,2027):
            tr=B[(B.o.dt.year!=yr)&(B.o>=desde)]; fac={k:float(np.clip(np.median(g.y/g.nc),0.5,2.5)) for k,g in tr[tr.k>=0].groupby('k') if len(g)>=8}
            te=B[B.o.dt.year==yr]; f.append(te.nc*te.k.map(lambda k:fac.get(k,1.0)))
        f=pd.concat(f); g=B[B.o>='2022-01-01']
        yrs={yr:(round(1-rm(g.nc[x.index],x.y)/rm(x.ltm,x.y),3),round(1-rm(f[x.index],x.y)/rm(x.ltm,x.y),3)) for yr,x in g.groupby(g.o.dt.year)}
        out[f'{thr}_{desde}']=dict(rmse_base=round(rm(g.nc,g.y)),rmse=round(rm(f,g.y)),frac=round(float((g.k>=0).mean()),3),anual=yrs)
        print(thr,desde,out[f'{thr}_{desde}'])
    fac={k:round(float(np.median(g.y/g.nc)),2) for k,g in B[(B.k>=0)&(B.o>='2021-10-01')].groupby('k')}; print('  factores 2021+',fac)
json.dump(out,open('/home/claude/work/q26/bt_perfil.json','w'),indent=1)
