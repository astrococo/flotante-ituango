"""Descarga caudales diarios del IDEAM (AQUARIUS WebPortal) para estaciones cercanas al embalse de Ituango.
Salida: datos/ideam/estaciones.csv, datos/ideam/conjuntos.csv, datos/ideam/q_<codigo>_<etiqueta>.csv, datos/ideam/registro.txt"""
import os, sys, traceback, pandas as pd
from colombia_hydrodata.utils.fetch import stations as st, aquarius as aq
O='datos/ideam'; os.makedirs(O,exist_ok=True)
log=open(f'{O}/registro.txt','w')
def L(*a): print(*a); log.write(' '.join(map(str,a))+'\n'); log.flush()
BB=(6.3,7.6,-76.3,-75.3)   # lat min, lat max, lon min, lon max (cuenca media del Cauca alrededor de Ituango)
S=st.fetch_df(); S=pd.DataFrame(S.drop(columns=[c for c in S.columns if c=='geometry'],errors='ignore'))
for c in ['latitude','longitude']: S[c]=pd.to_numeric(S[c],errors='coerce')
E=S[(S.latitude.between(BB[0],BB[1]))&(S.longitude.between(BB[2],BB[3]))]
E.to_csv(f'{O}/estaciones.csv',index=False); L('estaciones en el recuadro',len(E))
D=aq.aquarius_datasets(); D=pd.DataFrame(D)
ids=set(E['id'].astype(str))|{i.zfill(10) for i in E['id'].astype(str)}|{i.lstrip('0') for i in E['id'].astype(str)}
C=D[D['loc_id'].astype(str).isin(ids)]
C.to_csv(f'{O}/conjuntos.csv',index=False); L('conjuntos de esas estaciones',len(C)); L(C.groupby('param').size().to_string())
Q=C[C['param'].astype(str).str.upper().isin(['CAUDAL','NIVEL'])]
Q=Q[Q['label'].astype(str).str.contains('MEDIA_D|Q_MEDIA|NV_MEDIA',case=False,regex=True)]
for r in Q.itertuples():
    try:
        df=aq.dataset(int(r.wp_dset_id)); n=f"{O}/{str(r.param).lower()}_{r.loc_id}_{str(r.label).replace('/','_')}.csv"
        df.to_csv(n,index=False); L('ok',r.loc_id,r.param,r.label,len(df),df.timestamp.min(),df.timestamp.max())
    except Exception as e: L('error',r.loc_id,r.label,repr(e)[:200])
