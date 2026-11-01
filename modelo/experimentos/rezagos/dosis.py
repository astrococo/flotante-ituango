exec(open('/home/claude/work/q28/base.py').read())
D=d['2021-10-01':'2026-10-10']
W=pd.DataFrame({'mf':D.mf_tot.resample('W-SUN').sum(),'act':D.act.resample('W-SUN').sum(),'q':D.sitiopresa_f.resample('W-SUN').mean(),'qmax':D.sitiopresa_f.resample('W-SUN').max(),'op':D.opd.resample('W-SUN').min()})
W['rate']=np.where(W.act>=2,W.mf/W.act,np.nan)
# línea base local: mediana de la tasa en ±13 semanas excluyendo ±2 semanas
r=W.rate.values; base=[]
for i in range(len(W)):
    idx=[j for j in range(max(0,i-13),min(len(W),i+14)) if abs(j-i)>2]
    base.append(np.nanmedian(r[idx]))
W['base']=base; W['rel']=W.rate/W.base
out={}
for lag in [0,1,2,3,4]:
    x=W.qmax.shift(lag); bins=[0,1000,1500,1866,2300,5000]; g=pd.cut(x,bins)
    t=W.groupby(g).agg(n=('rel','count'),rel_med=('rel','median'),act_med=('act','median'))
    out[lag]={str(k):dict(n=int(v.n),rel=round(float(v.rel_med),2),dias=float(v.act_med)) for k,v in t.iterrows()}
    print('rezago',lag,'sem —',' | '.join(f"{k}: n={v['n']} ×{v['rel']} días {v['dias']}" for k,v in out[lag].items()))
json.dump(out,open('/home/claude/work/q28/dosis.json','w'),indent=1)
H=W[W.qmax>2300][['qmax','mf','act','rate','base','rel']].round(1); print(H.to_string())
