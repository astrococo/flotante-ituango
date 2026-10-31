import pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from scipy.stats import rankdata,t as T
E=pd.read_csv('/home/claude/work/site/datos/satelite/corredor/escenas.csv',parse_dates=['fecha'])
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
tr=sorted({c.rsplit('_',2)[0] for c in E.columns if c.endswith('_area_px')},key=lambda s:float(s[1:].split('_')[0]))
for z in tr:
    E[z]=E[z+'_veg_px']/E[z+'_valid_px'].clip(lower=1)*E[z+'_area_px']*0.04
    E.loc[E[z+'_valid_px']<0.6*E[z+'_area_px'],z]=np.nan
print('escenas',len(E),'| área de agua por tramo (ha):',{z:round(E[z+'_area_px'].iloc[0]*0.04) for z in tr})
print('mediana de vegetación por tramo (ha):',E[tr].median().round(1).to_dict(),'| escenas válidas:',E[tr].notna().sum().to_dict())
q=X.sitiopresa_f
def win(s,d,a,b): return s[(s.index>d+pd.Timedelta(days=a))&(s.index<=d+pd.Timedelta(days=b))].sum()
E=E[(E.fecha>=X.index.min()+pd.Timedelta(days=14))&(E.fecha<=X.index.max()-pd.Timedelta(days=28))].copy()
for k,s in [('ma',X.ma_tot),('mf',X.mf_tot),('tot',X.tot)]:
    E[k+'_prev']=[win(s,d,-14,0) for d in E.fecha];E[k+'_n2']=[win(s,d,0,14) for d in E.fecha];E[k+'_n4']=[win(s,d,14,28) for d in E.fecha]
E['q14']=[q[(q.index>d-pd.Timedelta(days=14))&(q.index<=d)].mean() for d in E.fecha]
E['m']=E.fecha.dt.month
def parcial(z,y,ctrl):
    B=E.dropna(subset=[z,y]+ctrl);r=lambda v:rankdata(v)
    def res(a,C):Xc=np.c_[np.ones(len(a)),C];return a-Xc@np.linalg.lstsq(Xc,a,rcond=None)[0]
    C=np.column_stack([r(B[c]) for c in ctrl]+[pd.get_dummies(B.m).values.astype(float)])
    e1,e2=res(r(B[z]),C),res(r(B[y]),C);rr=np.corrcoef(e1,e2)[0,1];n=len(B);tt=rr*np.sqrt((n-3)/(1-rr**2));return f"{rr:+.2f} (p={2*(1-T.cdf(abs(tt),n-3)):.3f}, n={n})"
print('\\nCorrelación parcial (rangos) del área por tramo con la extracción futura, controlando la extracción de las 2 semanas previas, el caudal reciente y el mes:')
for z in tr:
    print(f'  {z:12s} total sem 1–2 {parcial(z,"tot_n2",["tot_prev","q14"])} | sem 3–4 {parcial(z,"tot_n4",["tot_prev","q14"])} | macrófitas sem 1–2 {parcial(z,"ma_n2",["ma_prev","q14"])} | flotante sem 1–2 {parcial(z,"mf_n2",["mf_prev","q14"])}')
