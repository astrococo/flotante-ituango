import pandas as pd, numpy as np, json
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
P=json.load(open('/home/claude/work/site/modelo/params_v21.json'))
y='mf_tot'; B=pd.read_pickle('/home/claude/work/exp26/B_mf_tot.pkl'); p=dict(P[y])
tr=B[B.o<'2024-01-01']; gs=np.linspace(0,1,21); ah={}
for h,g in tr.groupby('h'): ah[h]=float(gs[np.argmin([rm(k*g.ew+(1-k)*g.ltm,g.y) for k in gs])])
S=0.5
B['nc']=(1-S)*(B.h.map(ah)*B.ew+(1-B.h.map(ah))*B.ltm)+S*B.ltm
B['r']=(B.y+50)/(B.nc+50)
Bq=B[B.o>='2022-01-01']
q=Bq.groupby('h').r.quantile([0.1,0.25,0.5,0.75,0.9]).unstack()
p['q']={str(c):(q[c].round(3).tolist() if c!=0.5 else [1.0]*13) for c in q.columns}; p['rmean']=Bq.groupby('h').r.mean().round(3).tolist()
met=[]
for h,g in Bq.groupby('h'):
    p50=g.nc; cov=float(((g.r>=q.loc[h,0.1])&(g.r<=q.loc[h,0.9])).mean())
    met.append(dict(h=int(h),clim=round(rm(g.ltm,g.y)),pers=round(rm(g.lvl8,g.y)),modelo=round(rm(p50,g.y)),mae=round(float(np.mean(abs(g.y-p50)))),
        skill_clim=round(1-rm(p50,g.y)/rm(g.ltm,g.y),3),skill_pers=round(1-rm(p50,g.y)/rm(g.lvl8,g.y),3),cobertura80=round(cov,2),n=len(g),media_obs=round(float(g.y.mean())),sesgo=round(float((p50-g.y).mean()))))
p['metricas']=met
cal=Bq[Bq.o<'2024-01-01']; val=Bq[Bq.o>='2024-01-01']; qq=cal.groupby('h').r.quantile([.1,.9]).unstack(); v=val.join(qq,on='h')
p['cobertura80_fuera_muestra']=round(float(((v.r>=v[0.1])&(v.r<=v[0.9])).mean()),3)
Bq=Bq.copy(); Bq['p50']=Bq.nc
# v1 con fechas corregidas, misma base de evaluación
a1={}
for h,g in tr.groupby('h'): a1[h]=float(gs[np.argmin([rm(k*g.lvl8+(1-k)*g.ltm,g.y) for k in gs])])
Bq['v1']=Bq.h.map(a1)*Bq.lvl8+(1-Bq.h.map(a1))*Bq.ltm
old=P[y]['skill_anual']
p['skill_anual']={str(yr):dict(v1=round(1-rm(g.v1,g.y)/rm(g.ltm,g.y),3),v21=old.get(str(yr),{}).get('v2'),v22=round(1-rm(g.p50,g.y)/rm(g.ltm,g.y),3)) for yr,g in Bq.groupby(Bq.o.dt.year)}
p['rmse_total']=dict(clim=round(rm(Bq.ltm,Bq.y)),pers=round(rm(Bq.lvl8,Bq.y)),v1=round(rm(Bq.v1,Bq.y)),v22=round(rm(Bq.p50,Bq.y)))
p.update(k=1.0,ewma_hl=6,a_h=[ah[h] for h in range(1,14)],shrink=S,lt_desde='2019-07-01',usa_caudal=False,
  valor_central='sin calibración por mediana: con calibración el error de 2026 subía (habilidad −0,12); sin ella la habilidad es ≥0 todos los años 2022–2026',k_regla='nivel = media exponencial (vida media 6 semanas) de semanas con operación completa; mezcla con la mediana histórica según el horizonte y encogimiento del 50 % hacia la mediana',
  nota_caudal='Sin caudal en el valor central: con fechas corregidas, el multiplicador de caudal aumentó el error 2022–2026 (RMSE 1.169–1.232 vs 1.096 sin él). La creciente se muestra como aviso.')
P[y]=p; P['version']='2.2 (1-nov-2026)'
print(json.dumps({k:p[k] for k in ['skill_anual','rmse_total','cobertura80_fuera_muestra','a_h']},indent=0))
json.dump(P,open('/home/claude/work/exp26/params_v22.json','w'),indent=1,ensure_ascii=False)
