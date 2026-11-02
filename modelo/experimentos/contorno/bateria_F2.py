"""Familia F (19 pruebas) con el contorno del usuario: distancias por el río, 10 m, óptico + Landsat + radar."""
import pandas as pd, numpy as np, json, warnings, sys; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/contorno/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J.get(src) or {},orient='index')
    if len(R): R.index=pd.to_datetime(R.index)
    return R.sort_index()
O,LS,RD=df('optico'),df('landsat'),df('radar')
S=O
for X in ((LS,) if 'sinradar' in sys.argv else (LS,RD)):
    if len(X): S=S.combine_first(X)     # mismo día: prevalece óptico, luego Landsat, luego radar
S=S[S.index>=I0]
TR=J['tramos']; k=lambda t:'t'+t.replace('..','_')
up=[k(t) for t in TR if float(t.split('..')[1])<=0]; dn=[k(t) for t in TR if float(t.split('..')[0])>=0]
lejos=[c for c in up if float(c[1:].split('_')[1])<=-10]          # más de 10 km aguas arriba
S['lejos']=S[lejos].sum(axis=1,min_count=max(1,len(lejos)-1)) if lejos else np.nan
Wk=S.resample('W-SUN').mean()
q=D.sitiopresa_f; lq=np.log(q); anq=lq-lq.rolling(365,min_periods=180).median()
qw=lambda hl: anq.ewm(halflife=hl).mean().resample('W-SUN').last().reindex(Wk.index)
d23=(q>2300).resample('W-SUN').sum().reindex(Wk.index); d23p=(q>2300).rolling(14).sum().resample('W-SUN').last().reindex(Wk.index)
Wd=D[I0:I1]; W2=pd.DataFrame({'mf':Wd.mf_tot.resample('W-SUN').sum(),'ma':Wd.ma_tot.resample('W-SUN').sum(),'a1':Wd.act.resample('W-SUN').sum(),'a2':Wd.actma.resample('W-SUN').sum(),
     'mec':Wd.mec.resample('W-SUN').sum(),'mfm':Wd.mf_mec_d.resample('W-SUN').sum()}).reindex(Wk.index)
W2['mfr']=(W2.mf/W2.a1).where(W2.a1>=2); W2['mar']=(W2.ma/W2.a2).where(W2.a2>=2); W2['sh']=(W2.mfm/W2.mec).where(W2.mec>200); W2.loc['2026-04-01':'2026-10-04','sh']=np.nan
W2['totr']=((W2.mf+W2.ma)/W2[['a1','a2']].max(axis=1)).where(W2[['a1','a2']].max(axis=1)>=2)
z=(Wd.op_mec==0).astype(int); racha=z.groupby((z!=z.shift()).cumsum()).cumsum().resample('W-SUN').last().reindex(Wk.index)
nx=lambda s:(s.shift(-1)+s.shift(-2))/2
def tst(n,x,y,method='spearman'):
    r,p,nn=shift_test(x,y,method=method); add('F. Satélite',n,r,p,dict(n=nn))
ret,bar,arr=Wk['ret'],Wk['bar'],Wk['arriba']
for hl in [3,7,14]: tst(f'Mancha retenida (0–2,5 km por el río) vs caudal (media exp. {hl} d)',qw(hl),ret)
tst('Cambio semanal de la mancha retenida vs días > 2.300 m³/s en la semana',d23,ret.diff())
tst('Ocupación de la barrera (100 m) vs caudal (media exp. 7 d)',qw(7),bar)
tst('Ocupación de la barrera vs días > 2.300 m³/s en las 2 semanas previas',d23p,bar)
tst('Mancha retenida vs fracción flotante de las 2 semanas siguientes',ret,nx(W2.sh))
tst('Mancha retenida vs flotante por día de las 2 semanas siguientes',ret,nx(W2.mfr))
tst('Mancha retenida vs macrófitas por día de las 2 semanas siguientes',ret,nx(W2.mar))
tst(f'Todo el contorno aguas arriba ({J["km_aguas_arriba"]} km) vs caudal (media exp. 7 d)',qw(7),arr)
tst('Todo el contorno aguas arriba vs extracción total por día de las 2 semanas siguientes',arr,nx(W2.totr))
tst('Tramo 0–2,5 km aguas abajo vs caudal (media exp. 7 d)',qw(7),Wk[dn[0]])
for c in [x for x in up if x in ('t-5.0_-2.5','t-10.0_-7.5','t-15.0_-12.5')]+[up[0]]:
    a,b=c[1:].split('_'); tst(f'Tramo {abs(float(b)):g}–{abs(float(a)):g} km aguas arriba vs caudal (media exp. 7 d)',qw(7),Wk[c])
tst('Mancha retenida en semanas con caudal > 2.300 m³/s (r punto-biserial)',(d23>0).astype(float),ret,method='pearson')
tst('Mancha retenida vs días seguidos sin mecanizado',racha,ret)
tst('Vegetación a más de 10 km aguas arriba vs mancha retenida 1–2 semanas después',Wk['lejos'],nx(ret))
json.dump(T,open('/home/claude/work/q31/bateria_F2'+('_sinradar' if 'sinradar' in sys.argv else '')+'.json','w'),indent=1,ensure_ascii=False)
for t in T: print(t['prueba'],t['estadistico'],t['p'],t.get('n'))
print('total',len(T))
