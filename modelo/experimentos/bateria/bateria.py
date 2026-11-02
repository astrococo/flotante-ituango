"""Batería de 100 pruebas pre-especificadas: caudal → material flotante / macrófitas / operación / satélite.
Cada prueba: estadístico, p bilateral por permutación que conserva la autocorrelación (desplazamiento circular del
predictor ≥ 26 semanas, o fechas de control del mismo mes en otros años para estudios de evento), y corrección de
Benjamini–Hochberg (FDR 5 %) sobre las 100."""
import pandas as pd, numpy as np, json, warnings, sys; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr
exec(open('/home/claude/work/prep.py').read())
d['opd']=((d.sin_operacion==0)&(d.mec_off==0)).astype(int)
X=pd.read_csv('/home/claude/work/q26/caudales_cuenca.csv',index_col=0,parse_dates=True)
e=pd.read_csv('/home/claude/work/prod/out/esfuerzo_diario.csv',parse_dates=['fecha'],index_col='fecha')
D=d.join(X[['virginia','bolombolo']],how='left').join(e[['op_mec','volquetas','viajes_mec']],how='left')
D['act']=(D.mf_tot>0).astype(int); D['actma']=(D.ma_tot>0).astype(int)
D['mfrate']=D.mf_tot.where(D.mf_tot>0); D['marate']=D.ma_tot.where(D.ma_tot>0)
D['mec']=D.mf_mec_d+D.ma_mec_d; D['sh']=(D.mf_mec_d/D.mec).where(D.mec>0)
D.loc['2026-04-01':'2026-10-04','sh']=np.nan
I0,I1=pd.Timestamp('2021-10-01'),pd.Timestamp('2026-10-10')
EST={'Sitio Presa':D.sitiopresa_f,'Olaya':D.olaya,'La Virginia':D.virginia,'Bolombolo':D.bolombolo,'La Pintada':D.pintada}
rng=np.random.default_rng(2026); T=[]
def add(fam,nombre,est,p,extra=None): T.append(dict(familia=fam,prueba=nombre,estadistico=None if est is None or not np.isfinite(est) else round(float(est),3),p=None if p is None else round(float(p),4),**(extra or {})))
def shift_test(x,y,n=999,min_shift=26,method='spearman'):
    z=pd.concat([x,y],axis=1).dropna(); 
    if len(z)<30: return np.nan,None,len(z)
    a=z.iloc[:,0].values; b=z.iloc[:,1].values; r0=pd.Series(a).corr(pd.Series(b),method=method)
    L=len(a); rs=[]
    for _ in range(n):
        ms=min(min_shift,L//3); k=int(rng.integers(ms,L-ms)); rs.append(pd.Series(np.roll(a,k)).corr(pd.Series(b),method=method))
    return r0,(np.sum(np.abs(rs)>=abs(r0))+1)/(n+1),len(z)
# ---------- A. estudios de evento (nivel normal ±1–4 meses fuera de la creciente) ----------
def picks(q,qq=0.9,sep=30):
    q=q[I0:'2026-08-31'].dropna(); thr=q.quantile(qq); pk=[]
    for t,v in q[q>thr].sort_values(ascending=False).items():
        if all(abs((t-p).days)>=sep for p in pk): pk.append(t)
    return sorted(pk),thr
def perfil(t,s,k0,k1):
    ab=pd.concat([s[t-pd.Timedelta(days=120):t-pd.Timedelta(days=29)],s[t+pd.Timedelta(days=57):t+pd.Timedelta(days=150)]]); base=ab.median()
    w=s[t+pd.Timedelta(days=7*k0):t+pd.Timedelta(days=7*k1+6)]
    return w.mean()/base if base>0 and w.notna().sum()>=2 else np.nan
def evento(q,s,k0,k1,n=400):
    pk,thr=picks(q); ev=np.nanmedian([perfil(t,s,k0,k1) for t in pk]); yrs=list(range(2021,2027)); C=[]
    for _ in range(n):
        rd=[]
        for t in pk:
            for _ in range(10):
                x=pd.Timestamp(year=int(rng.choice(yrs)),month=t.month,day=min(t.day,28))
                if I0<=x<=pd.Timestamp('2026-06-01') and all(abs((x-p).days)>45 for p in pk): rd.append(x); break
        C.append(np.nanmedian([perfil(x,s,k0,k1) for x in rd]))
    C=np.array(C); c=np.nanmedian(C); p=(np.sum(np.abs(np.log(C/c))>=abs(np.log(ev/c)))+1)/(len(C)+1)
    return ev,c,p,len(pk),thr
VENT=[('semana 0',0,0),('semana 1',1,1),('semana 2',2,2),('semanas 3–4',3,4),('semanas 5–8',5,8)]
for st,q in EST.items():
    for lab,k0,k1 in VENT:
        ev,c,p,n,thr=evento(q,D.mfrate,k0,k1); add('A. Evento flotante',f'{st}: flotante por día, {lab} tras creciente (P90 {round(thr)} m³/s)',ev,p,dict(control=round(float(c),3),eventos=n))
for st in ['Sitio Presa']:
    for lab,k0,k1 in VENT:
        ev,c,p,n,thr=evento(EST[st],D.marate,k0,k1); add('A. Evento macrófitas',f'{st}: macrófitas por día, {lab} tras creciente',ev,p,dict(control=round(float(c),3),eventos=n))
for lab,k0,k1 in VENT[:4]:
    ev,c,p,n,thr=evento(EST['Olaya'],D.marate,k0,k1); add('A. Evento macrófitas',f'Olaya: macrófitas por día, {lab} tras creciente',ev,p,dict(control=round(float(c),3),eventos=n))
print('A listo',len(T),flush=True)
# ---------- B. operación mecanizada según caudal (diario, oct-2021–2026) ----------
Dd=D[I0:I1]
for st,q in EST.items():
    r,p,n=shift_test(q[I0:I1],Dd.op_mec.astype(float),min_shift=180); add('B. Operación',f'{st}: caudal diario vs día con mecanizado (ρ)',r,p,dict(n=n))
for thr in [1866,2300]:
    x=(Dd.sitiopresa_f>thr).astype(float); r,p,n=shift_test(x,Dd.op_mec.astype(float),min_shift=180,method='pearson'); add('B. Operación',f'Sitio Presa > {thr} m³/s vs día con mecanizado (r)',r,p,dict(n=n,opera_si=round(float(Dd.op_mec[x==1].mean()),3),opera_no=round(float(Dd.op_mec[x==0].mean()),3)))
print('B listo',len(T),flush=True)
# ---------- C. composición (fracción flotante del mecanizado frente a su nivel de 26 semanas) ----------
W=pd.DataFrame({'mf':Dd.mf_mec_d.resample('W-SUN').sum(),'mec':Dd.mec.resample('W-SUN').sum()}); W['sh']=(W.mf/W.mec).where(W.mec>200)
W.loc['2026-04-01':'2026-10-04','sh']=np.nan
lg=np.log(W.sh/(1-W.sh)); ysh=lg-lg.shift(1).rolling(26,min_periods=8).median()
for st in ['Sitio Presa','La Virginia']:
    q=EST[st]; lq=np.log(q); an=lq-lq.rolling(365,min_periods=180).median()
    for hl in [7,14,28,42,56,84]:
        x=an.ewm(halflife=hl).mean().resample('W-SUN').last().reindex(W.index)
        r,p,n=shift_test(x,ysh,method='pearson'); add('C. Composición',f'{st}: fracción flotante vs caudal (media exp. {hl} d)',r,p,dict(n=n))
print('C listo',len(T),flush=True)
# ---------- D. mensual: anomalía de caudal → anomalía del extraído (preblanqueado AR1) ----------
from statsmodels.tsa.ar_model import AutoReg
DM=D['2019-08-01':'2026-09-30']
M=pd.DataFrame({'q':DM.sitiopresa_f.resample('MS').mean(),'mf':DM.mf_tot.resample('MS').sum(),'ma':DM.ma_tot.resample('MS').sum(),'a1':DM.act.resample('MS').sum(),'a2':DM.actma.resample('MS').sum()})
an=lambda s: np.log(s)-np.log(s).groupby(s.index.month).transform('median')
xq=an(M.q); ph=AutoReg(xq.dropna().values,lags=1,trend='c').fit().params; xe=xq-ph[0]-ph[1]*xq.shift(1)
for comp,col,ac in [('flotante','mf','a1'),('macrófitas','ma','a2')]:
    y=an((M[col]/M[ac].clip(lower=1)).clip(lower=1)); yf=y-ph[0]-ph[1]*y.shift(1)
    for L in range(3,9):
        r,p,n=shift_test(xe.shift(L),yf,min_shift=12,method='pearson'); add('D. Mensual',f'{comp} por día vs caudal {L} meses antes (preblanqueado)',r,p,dict(n=n))
print('D listo',len(T),flush=True)
# ---------- E. semanal preblanqueado ----------
WW=pd.DataFrame({'mf':Dd.mf_tot.resample('W-SUN').sum(),'ma':Dd.ma_tot.resample('W-SUN').sum(),'a1':Dd.act.resample('W-SUN').sum(),'a2':Dd.actma.resample('W-SUN').sum(),'q':Dd.sitiopresa_f.resample('W-SUN').max()})
anw=lambda s: np.log(s)-np.log(s).groupby(s.index.isocalendar().week.values).transform('median')
xw=anw(WW.q).interpolate(limit=2); fw=AutoReg(xw.dropna().values,lags=2,trend='n').fit().params; xwe=xw-fw[0]*xw.shift(1)-fw[1]*xw.shift(2)
for comp,col,ac in [('flotante','mf','a1'),('macrófitas','ma','a2')]:
    y=anw((WW[col]/WW[ac].clip(lower=1)).where(WW[ac]>=2).clip(lower=1)); yf=y-fw[0]*y.shift(1)-fw[1]*y.shift(2)
    for L in range(0,5):
        r,p,n=shift_test(xwe.shift(L),yf,method='pearson'); add('E. Semanal',f'{comp} por día vs caudal máximo {L} semanas antes (preblanqueado)',r,p,dict(n=n))
print('E listo',len(T),flush=True)
json.dump(T,open('/home/claude/work/q30/bateria_AE.json','w'),indent=1,ensure_ascii=False)
D.to_pickle('/home/claude/work/q30/D.pkl')
print(len(T))
