"""Familia F (19 pruebas): mancha retenida y corredor ±30 km (Sentinel-2 + Sentinel-1) frente a caudal y extracción.
Serie semanal: promedio de las mediciones de la semana (óptico si hay; si no, radar con el umbral calibrado)."""
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/retenido/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J[src],orient='index'); R.index=pd.to_datetime(R.index); return R.sort_index()
O=df('optico'); Rr=df('radar') if J.get('radar') else pd.DataFrame()
S=O.combine_first(Rr) if len(Rr) else O          # mismo día: prevalece el óptico
S=S[S.index>=I0]
Wk=S.resample('W-SUN').mean(); Wn=S.resample('W-SUN').count()
q=D.sitiopresa_f; lq=np.log(q); anq=lq-lq.rolling(365,min_periods=180).median()
qw=lambda hl: anq.ewm(halflife=hl).mean().resample('W-SUN').last().reindex(Wk.index)
d23=(q>2300).resample('W-SUN').sum().reindex(Wk.index)
d23p=(q>2300).rolling(14).sum().resample('W-SUN').last().reindex(Wk.index)
Wd=D[I0:I1]; W2=pd.DataFrame({'mf':Wd.mf_tot.resample('W-SUN').sum(),'ma':Wd.ma_tot.resample('W-SUN').sum(),'a1':Wd.act.resample('W-SUN').sum(),'a2':Wd.actma.resample('W-SUN').sum(),
     'mec':Wd.mec.resample('W-SUN').sum(),'mfm':Wd.mf_mec_d.resample('W-SUN').sum(),'op':Wd.op_mec.resample('W-SUN').sum()}).reindex(Wk.index)
W2['mfr']=(W2.mf/W2.a1).where(W2.a1>=2); W2['mar']=(W2.ma/W2.a2).where(W2.a2>=2); W2['sh']=(W2.mfm/W2.mec).where(W2.mec>200); W2.loc['2026-04-01':'2026-10-04','sh']=np.nan
# días sin extracción mecanizada acumulados (racha) al cierre de cada semana
z=(Wd.op_mec==0).astype(int); racha=z.groupby((z!=z.shift()).cumsum()).cumsum(); racha=racha.resample('W-SUN').last().reindex(Wk.index)
def tst(n,x,y,method='spearman'):
    r,p,nn=shift_test(x,y,method=method); add('F. Satélite',n,r,p,dict(n=nn))
ret=Wk.get('ret'); bar=Wk.get('bar')
for hl in [3,7,14]: tst(f'Mancha retenida (0–2,5 km) vs caudal (media exp. {hl} d)',qw(hl),ret)
tst('Cambio semanal de la mancha retenida vs días > 2.300 m³/s en la semana',d23,ret.diff())
tst('Ocupación de la barrera (franja 100 m) vs caudal (media exp. 7 d)',qw(7),bar)
tst('Ocupación de la barrera vs días > 2.300 m³/s en las 2 semanas previas',d23p,bar)
tst('Mancha retenida vs fracción flotante de las 2 semanas siguientes',ret,(W2.sh.shift(-1)+W2.sh.shift(-2))/2)
tst('Mancha retenida vs flotante por día de las 2 semanas siguientes',ret,(W2.mfr.shift(-1)+W2.mfr.shift(-2))/2)
tst('Mancha retenida vs macrófitas por día de las 2 semanas siguientes',ret,(W2.mar.shift(-1)+W2.mar.shift(-2))/2)
for t in ['0..2.5','2.5..7.5','7.5..15','15..22.5']:
    k='t'+t.replace('..','_'); k=[c for c in Wk.columns if c==f"t{t.split('..')[0]}_{t.split('..')[1]}"]
    col=k[0] if k else None
    tst(f'Tramo {t} km aguas abajo vs caudal (media exp. 7 d)',qw(7),Wk[col] if col else pd.Series(dtype=float))
for t in ['-7.5..-2.5','-15..-7.5','-22.5..-15','-30..-22.5']:
    col=f"t{t.split('..')[0]}_{t.split('..')[1]}"
    tst(f'Tramo {t} km aguas arriba vs caudal (media exp. 7 d)',qw(7),Wk[col] if col in Wk else pd.Series(dtype=float))
# evento: mancha retenida en semanas con > 2.300 frente a su nivel normal (±1–4 meses)
x=(d23>0).astype(float); tst('Mancha retenida en semanas con caudal > 2.300 m³/s (r punto-biserial)',x,ret,method='pearson')
tst('Mancha retenida vs días seguidos sin mecanizado',racha,ret)
json.dump(T,open('/home/claude/work/q30/bateria_F.json','w'),indent=1,ensure_ascii=False)
for t in T: print(t['prueba'],t['estadistico'],t['p'],t.get('n'))
Wk.join(W2).assign(q7=qw(7),d23=d23).to_pickle('/home/claude/work/q30/Wsat.pkl')
