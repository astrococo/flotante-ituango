exec(open('/home/claude/work/q26/ev.py').read().split("res={}")[0])
from scipy import signal
res={}
valid=d.index[(d.index>="2019-08-15")&(d.index<="2026-08-31")]
act=d.tot>0
rate=lambda c: d[c].where(act&(d.opd==1))   # m³ por día con extracción
for name,s,win in [('MF por día activo',rate('mf_tot'),((1,28),(0,27))),('MA por día activo',rate('ma_tot'),((1,28),(0,27))),
                   ('Tramo 2,5–7,5 km arriba',Cs['-7.5..-2.5'],((1,21),(0,20))),('Tramo 0–2,5 km arriba',Cs['-2.5..0'],((1,21),(0,20))),('Tramo 7,5–15 km arriba',Cs['-15..-7.5'],((1,21),(0,20))),
                   ('Puerto–barrera',Cs['bp'],((1,21),(0,20)))]:
    e=comp(s,[t for t in pk if t in valid],win); base=[]
    for _ in range(300):
        rd=[pd.Timestamp(year=int(rng.integers(2019,2027)),month=t.month,day=min(t.day,28)) for t in pk]; rd=[x for x in rd if x in valid]
        b=comp(s,rd,win)
        if len(b): base.append(np.median(b))
    base=np.array(base)
    res[name]=dict(n=len(e),mediana_evento=round(float(np.median(e)),2) if len(e) else None,mediana_azar=round(float(np.median(base)),2),p_valor=round(float((base>=np.median(e)).mean()),3) if len(e) else None)
    print(name,res[name])
# coherencia espectral (diaria, 2019-08 a 2026-09)
x=d.loc['2019-08-01':'2026-09-30']
for c in ['mf_tot','ma_tot','tot']:
    f,C2=signal.coherence(x.olaya.values-x.olaya.mean(),x[c].values-x[c].mean(),fs=1.0,nperseg=365)
    per=1/f[1:]; C2=C2[1:]
    bands={'7–14 d':(7,14),'15–45 d':(15,45),'46–120 d':(46,120),'121–365 d':(121,365)}
    print(c,{k:round(float(C2[(per>=a)&(per<=b)].mean()),2) for k,(a,b) in bands.items()})
# nivel de significancia aproximado de coherencia con K segmentos (Welch 50%): 1-0.05^(1/(K-1))
K=int((len(x)-365)/182)+1; print('segmentos',K,'umbral 95%',round(1-0.05**(1/(K-1)),2))
