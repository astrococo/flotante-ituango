exec(open('/home/claude/work/q28/base.py').read())
from scipy.stats import spearmanr
J=json.load(open('/home/claude/work/site/datos/satelite/app/serie.json'))
A=pd.concat([pd.DataFrame(J['serie']),pd.DataFrame(J['s1']),pd.DataFrame(J['landsat'])])[['f','t','a','b']]; A['f']=pd.to_datetime(A.f); A=A.groupby('f').mean()
out={}
for per,a in [('oct2021-2026','2021-10-01'),('2019-2026','2019-08-01')]:
    D=d[a:'2026-09-30']
    M=pd.DataFrame({'mf':D.mf_tot.resample('MS').sum(),'act':D.act.resample('MS').sum(),'q':D.sitiopresa_f.resample('MS').mean(),'qv':D.virginia.resample('MS').mean(),
                    'qx':D.sitiopresa_f.resample('MS').max(),'area_arriba':A.a.resample('MS').mean()[a:'2026-09-30'],'area_abajo':A.b.resample('MS').mean()[a:'2026-09-30']})
    M['rate']=M.mf/M.act.clip(lower=1)
    an=lambda s: s-s.groupby(s.index.month).transform('median')
    res={}
    for yv in ['mf','rate','area_arriba']:
        for xv in ['q','qx','qv']:
            r=[]
            for L in range(0,7):
                x=an(M[xv]).shift(L); y=an(M[yv]); z=pd.concat([x,y],axis=1).dropna()
                rr,p=spearmanr(z.iloc[:,0],z.iloc[:,1]); r.append((L,round(float(rr),2),round(float(p),3),len(z)))
            res[f'{yv}~{xv}']=r
            print(per,f'{yv:12s}~{xv:3s}',' '.join(f"{L}m:{rr:+.2f}{'*' if p<0.05 else ''}" for L,rr,p,n in r),'n',r[0][3])
    out[per]=res
json.dump(out,open('/home/claude/work/q28/mensual.json','w'),indent=1)
