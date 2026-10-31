import pickle,pandas as pd,numpy as np,re,warnings;warnings.filterwarnings('ignore')
from openpyxl.utils import column_index_from_string as ci
T=pickle.load(open('tidy_aj.pkl','rb'))
def plate(s): return re.sub(r'[^A-Z0-9]','',str(s).upper())
res={}
for k,vcols,tcol,vol in [('mamec',[c for c in T['mamec'][1] if 2<=ci(c)<=26],'AA','AB'),('mfmec',[c for c in T['mfmec'][1] if 2<=ci(c)<=25],'Z','AA')]:
    df,h=T[k];df=df.copy()
    tr=df[vcols].apply(pd.to_numeric,errors='coerce').fillna(0)
    rep_t=pd.to_numeric(df[tcol],errors='coerce').fillna(0);rep_v=pd.to_numeric(df[vol],errors='coerce').fillna(0)
    exp_v=[];omit=[];mult=[];fx=[]
    for i,r in df.iterrows():
        f=r.get('_f_'+vol);f=f if isinstance(f,str) else ''
        co=dict((c,float(x)) for c,x in re.findall(r'\(([A-Z]+)\d+\*([\d.]+)\)',f))
        m=re.search(r'\)\)\*([\d.]+)$',f);mu=float(m.group(1)) if m else 1.0
        om=[c for c in vcols if tr.at[i,c]!=0 and c not in co]
        omit.append(om);mult.append(mu);fx.append(bool(f))
        exp_v.append(mu*sum(co.get(c,0)*tr.at[i,c] for c in vcols))
    df['viajes_sum']=tr.sum(1);df['viajes_rep']=rep_t;df['vol_rep']=rep_v;df['vol_formula']=exp_v;df['omitidas']=omit;df['mult']=mult;df['tiene_formula']=fx
    df['vehiculos']=(tr>0).sum(1)
    bad_t=df[(df.viajes_sum-df.viajes_rep).abs()>0.01];bad_o=df[df.omitidas.str.len()>0];nof=df[(~df.tiene_formula)&(df.vol_rep!=0)]
    print(f'== {k}: filas {len(df)} | total viajes informado ≠ suma por vehículo: {len(bad_t)} filas, diferencia {(bad_t.viajes_sum-bad_t.viajes_rep).sum():.1f} viajes')
    print('   ejemplos:',bad_t[['row','fecha','viajes_sum','viajes_rep','_f_'+tcol]].head(8).values.tolist())
    print(f'   vehículos con viajes fuera de la fórmula de volumen: {len(bad_o)} filas',bad_o[['row','fecha','omitidas']].head(10).values.tolist())
    print(f'   volumen sin fórmula (valor fijo): {len(nof)} filas, {nof.vol_rep.sum():.1f} m3', nof[['row','fecha','vol_rep']].head(5).values.tolist())
    # coeficientes por vehículo usados
    co_all={}
    for f in df['_f_'+vol].dropna().astype(str):
        for c,x in re.findall(r'\(([A-Z]+)\d+\*([\d.]+)\)',f): co_all.setdefault(plate(h[c]),set()).add(float(x))
    print('   m3 por viaje según fórmulas:',{p:sorted(v) for p,v in co_all.items()})
    print('   multiplicador global:',pd.Series(mult).value_counts().to_dict())
    df.columns=[c for c in df.columns]
    res[k]=(df,{c:plate(h[c]) for c in vcols},tr)
pickle.dump(res,open('mec_aj.pkl','wb'))
