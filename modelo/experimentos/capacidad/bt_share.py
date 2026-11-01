import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
P=json.load(open('/home/claude/work/params_v21.json'))['mf_tot']
B=pd.read_pickle('/home/claude/work/exp26/B_mf_tot.pkl').merge(backtest('mf_tot')[['o','h','mult']],on=['o','h'],how='inner')
B['m']=np.clip(np.sqrt(B.mult),0.7,1.5); s=P['shrink']; a=B.h.map(lambda h:P['a_h'][h-1])
B['nc']=((1-s)*(a*B.ew+(1-a)*B.ltm)+s*B.ltm)*B.m
B['tgt']=B.o+pd.to_timedelta(B.h*7,unit='D')
# fracción flotante semanal del mecanizado y su nivel
Dd=pd.read_pickle('/home/claude/work/q29/D.pkl'); Dd['mec']=Dd.mf_mec+Dd.ma_mec
Wf=pd.DataFrame({'mf':d.mf_mec_d.resample('W-SUN').sum(),'mec':(d.mf_mec_d+d.ma_mec_d).resample('W-SUN').sum()})
Wf['sh']=(Wf.mf/Wf.mec).where(Wf.mec>200)
Wf.loc['2026-04-01':'2026-10-04','sh']=np.nan
lg=lambda p: np.log(p/(1-p))
lq=np.log(d.sitiopresa_f); anq=lq-lq.rolling(365,min_periods=180).median()
out={}
for hl in [28,42,56]:
    ew=anq.ewm(halflife=hl).mean()
    B['x_o']=B.o.map(lambda t: ew.get(t,np.nan))                       # conocido al origen (persistencia)
    B['x_t']=B.tgt.map(lambda t: ew.get(t,np.nan))                     # caudal real futuro (cota superior)
    B['shl']=B.o.map(lambda t: lg(Wf.sh[:t].dropna().tail(26).clip(0.05,0.95)).median())
    # coeficiente: logit(fracción semanal) − nivel ~ x, ajustado dejando fuera el año
    Z=pd.DataFrame({'y':lg(Wf.sh.clip(0.05,0.95)),'x':ew.resample('W-SUN').last().reindex(Wf.index)})
    Z['lvl']=Z.y.shift(1).rolling(26,min_periods=8).median(); Z['r']=Z.y-Z.lvl; Z=Z.dropna()
    for var in ['x_o','x_t']:
        f=[]
        for yr in range(2022,2027):
            zt=Z[Z.index.year!=yr]; b=np.polyfit(zt.x,zt.r,1)[0]
            te=B[B.o.dt.year==yr]; ex=lambda l: 1/(1+np.exp(-l))
            fac=(ex(te.shl+b*te[var].fillna(0))/ex(te.shl)).clip(0.6,1.6)
            mfm=te.nc*(1-0.03)  # el manual es ~3 % del flotante; se aplica el factor solo a la parte mecanizada
            f.append(te.nc*0.03+mfm*fac)
        f=pd.concat(f); g=B[B.o>='2022-01-01']
        out[f'{hl}_{var}']=dict(rmse_base=round(rm(g.nc,g.y)),rmse=round(rm(f[g.index],g.y)),anual={int(yr):(round(1-rm(x.nc,x.y)/rm(x.ltm,x.y),3),round(1-rm(f[x.index],x.y)/rm(x.ltm,x.y),3)) for yr,x in g.groupby(g.o.dt.year)})
        print(hl,var,out[f'{hl}_{var}'])
json.dump(out,open('/home/claude/work/q29/bt_share.json','w'),indent=1)
