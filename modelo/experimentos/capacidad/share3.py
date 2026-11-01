import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr, pearsonr
D=pd.read_pickle('/home/claude/work/q29/D.pkl'); D['mec']=D.mf_mec+D.ma_mec
Qd=D.sitiopresa_f; lq=np.log(Qd)
anq=lq-lq.rolling(365,min_periods=180).median()          # anomalía causal respecto al año previo
W=pd.read_pickle('/home/claude/work/q29/Wsh.pkl')
W['shl']=np.log(W.sh/(1-W.sh).clip(lower=0.02)).clip(-4,4)  # logit
res={}
best=None
for hl in [3,7,10,14,21,28,42,56]:
    ew=anq.ewm(halflife=hl).mean()          # incluye el día; promedio semanal
    x=ew.resample('W-SUN').mean().reindex(W.index)
    # quitar el nivel lento de la fracción (mediana de 26 semanas previas, causal)
    lvl=W.shl.shift(1).rolling(26,min_periods=8).median(); y=W.shl-lvl
    z=pd.concat([x,y],axis=1).dropna(); tr=z[z.index<'2025-01-01']; te=z[z.index>='2025-01-01']
    r_tr=pearsonr(tr.iloc[:,0],tr.iloc[:,1])[0]; r_te=pearsonr(te.iloc[:,0],te.iloc[:,1])[0]
    res[hl]=(round(r_tr,3),round(r_te,3),len(tr),len(te)); print('vida media',hl,'d  r entrenamiento',round(r_tr,2),' r validación 2025–26',round(r_te,2),len(tr),len(te))
json.dump(res,open('/home/claude/work/q29/share3.json','w'))
