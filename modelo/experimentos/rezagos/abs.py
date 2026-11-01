exec(open('/home/claude/work/q28/base.py').read())
q=d.sitiopresa_f
E=pd.read_csv('/home/claude/work/q28/eventos.csv',parse_dates=['pico'])
pk=list(E.pico)
def perfil(t):
    # línea base: mediana de m³/día-activo en ventanas [-120,-29] y [+57,+150] días (fuera de la creciente)
    a=d.loc[t-pd.Timedelta(days=120):t-pd.Timedelta(days=29)]; b=d.loc[t+pd.Timedelta(days=57):t+pd.Timedelta(days=150)]
    ab=pd.concat([a,b]); base=ab.mf_tot[ab.act==1].median()
    out=[]
    for k in range(-2,8):
        w=d.loc[t+pd.Timedelta(days=7*k):t+pd.Timedelta(days=7*k+6)]
        rate=w.mf_tot[w.act==1].mean() if w.act.sum()>=2 else np.nan
        out.append((rate/base if base>0 else np.nan, w.act.sum(), w.mf_tot.sum()-7*base*ab.act.mean()))
    return base,out
rows=[];P=[];A=[];V=[]
for t in pk:
    base,o=perfil(t); P.append([x[0] for x in o]); A.append([x[1] for x in o]); V.append([x[2] for x in o])
P=np.array(P,float); A=np.array(A,float); V=np.array(V,float)
lab=[f's{k}' for k in range(-2,8)]
print('base m³/día activo (mediana de eventos):',)
print('razón m³/día-activo vs línea base — mediana:',dict(zip(lab,np.round(np.nanmedian(P,0),2))))
print('   eventos >1:',dict(zip(lab,[int((P[:,i]>1).sum()) for i in range(P.shape[1])])),'n',dict(zip(lab,[int(np.isfinite(P[:,i]).sum()) for i in range(P.shape[1])])))
print('días con extracción por semana — mediana:',dict(zip(lab,np.nanmedian(A,0))))
print('m³ por semana sobre la línea base — mediana:',dict(zip(lab,np.round(np.nanmedian(V,0)))),' suma s1–s7 mediana',round(float(np.nanmedian(V[:,3:].sum(1)))))
# control: mismas fechas (mes-día) en otros años dentro del periodo
rng=np.random.default_rng(7); C=[]
yrs=[2021,2022,2023,2024,2025,2026]
for _ in range(300):
    pc=[]
    for t in pk:
        for _ in range(10):
            y=int(rng.choice(yrs)); 
            try: x=pd.Timestamp(year=y,month=t.month,day=min(t.day,28))
            except: continue
            if I0<=x<=pd.Timestamp('2026-06-01') and all(abs((x-p).days)>45 for p in pk): pc.append(x); break
    Pc=np.array([[z[0] for z in perfil(x)[1]] for x in pc],float); C.append(np.nanmedian(Pc,0))
C=np.array(C); med=np.nanmedian(P,0)
print('control (fechas sin creciente) mediana:',dict(zip(lab,np.round(np.median(C,0),2))))
print('p (control ≥ evento):',dict(zip(lab,[round(float((C[:,i]>=med[i]).mean()),3) for i in range(len(lab))])))
json.dump(dict(semanas=lab,razon_evento=np.round(med,3).tolist(),razon_control=np.round(np.median(C,0),3).tolist(),p=[round(float((C[:,i]>=med[i]).mean()),3) for i in range(len(lab))],
  eventos_mayor_1=[int((P[:,i]>1).sum()) for i in range(P.shape[1])],n=[int(np.isfinite(P[:,i]).sum()) for i in range(P.shape[1])],
  dias_activos=np.nanmedian(A,0).tolist(),m3_sobre_base=np.round(np.nanmedian(V,0)).tolist()),open('/home/claude/work/q28/perfil_abs.json','w'),indent=1)
np.save('/home/claude/work/q28/P.npy',P)
