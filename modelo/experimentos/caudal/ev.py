import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
d['opd']=((d.sin_operacion==0)&(d.mec_off==0)).astype(int)
J=json.load(open('/home/claude/work/site/datos/satelite/app/serie.json'))
A=pd.concat([pd.DataFrame(J['serie']),pd.DataFrame(J['s1']),pd.DataFrame(J['landsat'])])[['f','t','a','b']]; A['f']=pd.to_datetime(A.f)
A=A.groupby('f').mean()
C=json.load(open('/home/claude/work/site/datos/satelite/corredor/serie.json')); Cs=pd.DataFrame(C['serie']); Cs['f']=pd.to_datetime(Cs.f); Cs=Cs.set_index('f')
up=[t for t in C['tramos'] if float(t.split('..')[1])<=0]; Cs['up']=Cs[up].sum(axis=1,min_count=len(up))
q=d.olaya
# eventos: picos diarios de Olaya > P90 separados ≥ 30 días
thr=q.quantile(0.9); pk=[]
for t,v in q[q>thr].sort_values(ascending=False).items():
    if all(abs((t-p).days)>=30 for p in pk): pk.append(t)
pk=sorted(pk); print('umbral P90 Olaya',round(thr),'eventos',len(pk))
rng=np.random.default_rng(0)
def comp(series,days,win,agg='sum',ops=None):
    out=[]
    for t in days:
        a=series[t-pd.Timedelta(days=win[0][1]):t-pd.Timedelta(days=win[0][0])]; b=series[t+pd.Timedelta(days=win[1][0]):t+pd.Timedelta(days=win[1][1])]
        if len(a.dropna())<2 or len(b.dropna())<2: continue
        out.append(b.mean()/a.mean() if a.mean()>0 else np.nan)
    return np.array([x for x in out if np.isfinite(x)])
res={}
valid=d.index[(d.index>='2019-08-15')&(d.index<='2026-08-31')]
for name,s,win in [('MF extraído',d.mf_tot,((1,28),(0,27))),('MA extraído',d.ma_tot,((1,28),(0,27))),('MF extraído 4-8 sem',d.mf_tot,((1,28),(28,55))),('MA extraído 4-8 sem',d.ma_tot,((1,28),(28,55))),
                   ('Área aguas arriba barrera',A.a,((1,21),(0,20))),('Área aguas abajo barrera',A.b,((1,21),(0,20))),('Corredor 0–30 km arriba',Cs.up,((1,21),(0,20)))]:
    e=comp(s,[t for t in pk if t in valid],win)
    # base: fechas al azar del mismo mes (control estacional)
    base=[]
    for _ in range(300):
        rd=[pd.Timestamp(year=int(rng.integers(2019,2027)),month=t.month,day=min(t.day,28)) for t in pk]
        rd=[x for x in rd if x in valid]
        b=comp(s,rd,win); 
        if len(b): base.append(np.median(b))
    base=np.array(base)
    res[name]=dict(n=len(e),mediana_evento=round(float(np.median(e)),2) if len(e) else None,mediana_azar=round(float(np.median(base)),2),
                  p_valor=round(float((base>=np.median(e)).mean()),3) if len(e) else None)
    print(name,res[name])
json.dump(res,open('/home/claude/work/q26/eventos.json','w'),indent=1,ensure_ascii=False)
