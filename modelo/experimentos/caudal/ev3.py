exec(open('/home/claude/work/q26/ev.py').read().split("thr=q.quantile")[0])
res={}
def picks(q,qq=0.9,sep=30):
    thr=q.quantile(qq); pk=[]
    for t,v in q[q>thr].sort_values(ascending=False).items():
        if all(abs((t-p).days)>=sep for p in pk): pk.append(t)
    return sorted(pk),thr
def comp(series,days,win):
    out=[]
    for t in days:
        a=series[t-pd.Timedelta(days=win[0][1]):t-pd.Timedelta(days=win[0][0])]; b=series[t+pd.Timedelta(days=win[1][0]):t+pd.Timedelta(days=win[1][1])]
        if len(a.dropna())<2 or len(b.dropna())<2 or a.mean()<=0: continue
        out.append(b.mean()/a.mean())
    return np.array(out)
rng=np.random.default_rng(1)
inter=(d.sitiopresa-d.olaya); inter=inter[inter.index>='2021-10-01']
for qname,qs in [('Sitio Presa observado',d.sitiopresa.dropna()),('Cuenca intermedia (Sitio Presa − Olaya)',inter.dropna()),('Olaya, alza de 3 días',(d.olaya-d.olaya.shift(3)).dropna())]:
    pk,thr=picks(qs); valid=qs.index[(qs.index<=pd.Timestamp('2026-08-31'))]
    pk=[t for t in pk if t in valid and t>=pd.Timestamp('2019-08-15')]
    print('\n'+qname,'umbral',round(thr),'eventos',len(pk))
    for name,s,win in [('MF extraído 0–4 sem',d.mf_tot,((1,28),(0,27))),('MA extraído 0–4 sem',d.ma_tot,((1,28),(0,27))),('MF extraído 4–8 sem',d.mf_tot,((1,28),(28,55))),('MA extraído 4–8 sem',d.ma_tot,((1,28),(28,55))),
                       ('Área arriba barrera',A.a,((1,21),(0,20))),('Área abajo barrera',A.b,((1,21),(0,20)))]:
        e=comp(s,pk,win); base=[]
        for _ in range(300):
            rd=[]
            for t in pk:
                yrs=sorted(set(valid.year)); y=int(rng.choice(yrs)); x=pd.Timestamp(year=y,month=t.month,day=min(t.day,28))
                if x in valid: rd.append(x)
            b=comp(s,rd,win)
            if len(b): base.append(np.median(b))
        base=np.array(base); r=dict(n=len(e),evento=round(float(np.median(e)),2),azar=round(float(np.median(base)),2),p=round(float((base>=np.median(e)).mean()),3))
        res[f'{qname} | {name}']=r; print(' ',name,r)
json.dump(res,open('/home/claude/work/q26/eventos2.json','w'),indent=1,ensure_ascii=False)
