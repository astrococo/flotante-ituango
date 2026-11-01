import pandas as pd, numpy as np, json, unicodedata, re, warnings; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr
x=pd.read_pickle('/home/claude/work/q29_obs.pkl')
D=pd.read_pickle('/home/claude/work/q29/D.pkl')
falta=r'no hay material|poco material|sin material|escaso material|no se evidencia material|ausencia de material|baja presencia de material|no habia material|poca presencia|material muy distante|disponibilidad de material|no se cont[oó] con material|falta de material|material insuficiente|no fue posible confinar|no logr[oó] confinar|desabastec'
cond=r'caudal|creciente|nivel del rio|nivel del embalse|aumento del nivel|corriente|viento|lluvia|tormenta|riesgo'
abund=r'gran cantidad|abundante|mucho material|alta presencia|alta cantidad|bastante material|material suficiente|acumul|represad|presion|fuerza tangencial|ruptura|rompi'
for k,p in [('falta',falta),('condiciones',cond),('abundancia',abund)]: x[k]=x.t.str.contains(p,regex=True)
x=x.reindex(D.index)
D=D.join(x[['falta','condiciones','abundancia']].fillna(False))
print(D[['falta','condiciones','abundancia']].sum().to_dict(),' periodo',D.index.min().date(),D.index.max().date())
print(D[['falta','condiciones','abundancia']].groupby(D.index.year).sum().to_string())
lq=np.log(D.sitiopresa_f); anq=lq-lq.rolling(365,min_periods=180).median()
res={}
for k in ['falta','abundancia']:
    for hl in [7,21,42,56]:
        ew=anq.ewm(halflife=hl).mean()
        b=pd.qcut(ew,4,labels=['Q1 seco','Q2','Q3','Q4 húmedo'])
        t=D.groupby(b)[k].mean().round(3)
        res[f'{k}_{hl}']=t.to_dict(); print(k,'vida media',hl,'d',t.to_dict())
for t,o in x[x.falta.fillna(False)].obs.head(12).items(): print(t.date(), str(o)[:200])
D.to_pickle('/home/claude/work/q29/D2.pkl'); json.dump(res,open('/home/claude/work/q29/falta.json','w'),indent=1,ensure_ascii=False)
