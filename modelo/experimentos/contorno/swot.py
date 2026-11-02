import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
E='/home/claude/work/site/datos/satelite/earthdata/'
N=pd.read_csv(E+'swot_nodos.csv',dtype={'node_id':str}); S=pd.read_csv(E+'swot_series.csv',dtype={'node_id':str})
print('filas',len(S),'cols',list(S.columns)[:12])
S=S[pd.to_numeric(S.wse,errors='coerce').between(200,600)].copy(); S['wse']=S.wse.astype(float)
if 'node_q' in S: S=S[pd.to_numeric(S.node_q,errors='coerce')<=1]
if 'wse_u' in S: S=S[pd.to_numeric(S.wse_u,errors='coerce')<0.5]
S['t']=pd.to_datetime(S.time_str.str.slice(0,19),errors='coerce'); S=S.dropna(subset=['t']); S['fecha']=S.t.dt.normalize()
S=S.merge(N[['node_id','km_rio']],on='node_id'); S=S.dropna(subset=['km_rio'])
print('válidas',len(S),'nodos',S.node_id.nunique(),'fechas',S.fecha.nunique(),S.fecha.min(),S.fecha.max())
P=[]
for f,g in S.groupby('fecha'):
    near=g[g.km_rio.between(-2.5,3.6)]; up=g[g.km_rio<0]
    sl=np.polyfit(up.km_rio,up.wse,1)[0] if len(up)>=10 and up.km_rio.max()-up.km_rio.min()>5 else np.nan
    P.append(dict(fecha=f,n=len(g),wse_barrera=near.wse.median() if len(near)>=3 else np.nan,pend_m_km=sl,km_min=g.km_rio.min(),km_max=g.km_rio.max(),
       wse_lejos=g[g.km_rio<-15].wse.median() if (g.km_rio<-15).sum()>=3 else np.nan))
P=pd.DataFrame(P).set_index('fecha'); print(P.describe().round(2).T)
q=D.sitiopresa_f.reindex(P.index); P['q']=q.values
print('rho nivel-barrera vs caudal',P.wse_barrera.corr(P.q,method='spearman'),'pendiente vs caudal',P.pend_m_km.corr(P.q,method='spearman'), 'lejos-barrera vs q',(P.wse_lejos-P.wse_barrera).corr(P.q,method='spearman'))
# perfil medio por tramo de 1 km
pr=S.assign(k=np.floor(S.km_rio)).groupby('k').wse.agg(['median','std','count']).round(2); print(pr)
J=json.load(open('/home/claude/work/site/datos/satelite/contorno/serie.json')); O=pd.DataFrame.from_dict(J['optico'],orient='index'); O.index=pd.to_datetime(O.index)
res={}
for z in ['ret','arriba','bar']:
    s=O[z].dropna(); pr_=[]
    for f,r in P.dropna(subset=['wse_barrera']).iterrows():
        d=np.abs((s.index-f).days); k=d.argmin()
        if d[k]<=5: pr_.append((r.wse_barrera,s.iloc[k]))
    if len(pr_)>=8: a=np.array(pr_); res[z]=dict(n=len(a),rho=round(float(pd.Series(a[:,0]).corr(pd.Series(a[:,1]),method='spearman')),3))
print(res)
# comparar con la columna 'nivel' de los datos
nv=D.nivel.reindex(P.index); m=P.wse_barrera.notna()&nv.notna()
if m.sum()>5: print('nivel (datos) vs SWOT', round(np.corrcoef(nv[m],P.wse_barrera[m])[0,1],3), 'diferencia mediana',round(float((P.wse_barrera[m]-nv[m]).median()),2))
out=dict(nodos=int(S.node_id.nunique()),fechas=int(S.fecha.nunique()),desde=str(S.fecha.min().date()),hasta=str(S.fecha.max().date()),
  wse_barrera=dict(mediana=round(float(P.wse_barrera.median()),2),min=round(float(P.wse_barrera.min()),2),max=round(float(P.wse_barrera.max()),2)),
  pendiente_m_km=round(float(P.pend_m_km.median()),3), rho_nivel_caudal=round(float(P.wse_barrera.corr(P.q,method='spearman')),3),
  rho_pend_caudal=round(float(P.pend_m_km.corr(P.q,method='spearman')),3), veg_vs_nivel=res,
  perfil=[dict(km=float(k),wse=float(r['median']),n=int(r['count'])) for k,r in pr.iterrows()],
  serie=[dict(fecha=str(f.date()),wse_barrera=None if np.isnan(r.wse_barrera) else round(float(r.wse_barrera),2),pend=None if np.isnan(r.pend_m_km) else round(float(r.pend_m_km),3),q=None if np.isnan(r.q) else round(float(r.q))) for f,r in P.iterrows()])
json.dump(out,open('/home/claude/work/q31/swot_res.json','w'),indent=1)
