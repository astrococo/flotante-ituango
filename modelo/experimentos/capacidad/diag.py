import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr
exec(open('/home/claude/work/prep.py').read())
e=pd.read_csv('/home/claude/work/prod/out/esfuerzo_diario.csv',parse_dates=['fecha'],index_col='fecha')
D=e.join(d[['sitiopresa_f','olaya','mf_tot','ma_tot']],how='left')['2021-10-01':]
D['mec']=D.mf_mec+D.ma_mec
o=D[(D.op_mec==1)&(D.volquetas>0)&(D.viajes_mec>0)].copy()
o['vpv']=o.viajes_mec/o.volquetas; o['m3pv']=o.mec/o.volquetas; o['mfsh']=o.mf_mec/o.mec.clip(lower=1)
print('días operados',len(o)); print(o[['volquetas','viajes_mec','vpv','m3pv','mfsh','hora_inicio']].describe().round(2).to_string())
# ¿limitado por capacidad? variación de viajes por volqueta y su relación con caudal (mismo día y rezagos)
for L in [0,3,7,14,21,28,42]:
    qL=D.sitiopresa_f.rolling(7).mean().shift(L).reindex(o.index)
    print('rezago',L,'d  ρ(viajes/volqueta, Q7)',round(spearmanr(qL,o.vpv,nan_policy='omit')[0],2),' ρ(fracción flotante, Q7)',round(spearmanr(qL,o.mfsh,nan_policy='omit')[0],2),' ρ(m³ MF/volqueta)',round(spearmanr(qL,o.mf_mec/o.volquetas,nan_policy='omit')[0],2))
# volquetas y viajes por año
print(o.groupby(o.index.year)[['volquetas','vpv','m3pv','mfsh','hora_inicio']].median().round(2))
o.to_pickle('/home/claude/work/q29/o.pkl'); D.to_pickle('/home/claude/work/q29/D.pkl')
