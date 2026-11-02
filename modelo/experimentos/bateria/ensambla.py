import json, numpy as np
AE=json.load(open('q30/bateria_AE.json')); C=json.load(open('q30/bateria_C.json')); F=json.load(open('q30/bateria_F.json')); G=json.load(open('q30/bateria_G.json'))
fam=lambda t: t['familia'][0]
T=[t for t in AE if fam(t)!='C']+C+F+G
T=sorted(T,key=lambda t:t['familia'])
print('total',len(T),{f:sum(fam(t)==f for t in T) for f in 'ABCDEFG'})
ps=np.array([t['p'] if t['p'] is not None and t['p']==t['p'] else np.nan for t in T]); ok=~np.isnan(ps); m=ok.sum()
o=np.argsort(np.where(ok,ps,9)); q=np.full(len(ps),np.nan); prev=1.0
for rank in range(m,0,-1):
    i=o[rank-1]; prev=min(prev,ps[i]*m/rank); q[i]=prev
for t,qq in zip(T,q): t['q']=None if np.isnan(qq) else round(float(qq),4)
sig=[t for t in T if t['q'] is not None and t['q']<0.10]
print('evaluables',int(m),'q<0.10:',len(sig))
for t in sorted(sig,key=lambda t:t['q']): print(f"{t['familia'][:2]} {t['q']:.4f} {t['p']} {t['estadistico']}  {t['prueba']}")
json.dump(T,open('q30/bateria_100.json','w'),indent=1,ensure_ascii=False)
