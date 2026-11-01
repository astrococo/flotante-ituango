"""Descarga el histórico de 15 min de HydroForecast (/api/historical) mes a mes, 2015–hoy,
y guarda el resumen diario (media, mínimo, máximo, nº de registros) de cada columna en datos/hf/historico_diario.csv.
También guarda el histórico horario de Sitio Presa y Olaya (datos/hf/historico_horario.csv.gz)."""
import json, urllib.request, pandas as pd, datetime as dt, time
B='https://jdguarnizor-hydroforecast-ituango.hf.space/api/historical'
fr=[]; log=open('datos/hf/historico_registro.txt','w')
m=pd.Timestamp('2015-01-01'); fin=pd.Timestamp(dt.date.today())+pd.Timedelta(days=1)
while m<fin:
    n=min(m+pd.DateOffset(months=1),fin)
    u=f'{B}?desde={m:%Y-%m-%d}&hasta={n:%Y-%m-%d}'
    for k in range(3):
        try:
            d=json.loads(urllib.request.urlopen(u,timeout=180).read()); D=pd.DataFrame(d.get('data',[])); fr.append(D)
            log.write(f'{m:%Y-%m} {len(D)} {list(D.columns)} {D.notna().sum().to_dict() if len(D) else {}}\n'); break
        except Exception as e:
            log.write(f'{m:%Y-%m} error {e}\n'); time.sleep(10)
    log.flush(); m=n
A=pd.concat(fr).drop_duplicates('Fecha'); A['Fecha']=pd.to_datetime(A.Fecha); A=A.set_index('Fecha').sort_index()
A=A.apply(pd.to_numeric,errors='coerce')
D=A.resample('D').agg(['mean','min','max','count']); D.columns=[f'{a}_{b}' for a,b in D.columns]
D.round(2).to_csv('datos/hf/historico_diario.csv')
A.resample('h').mean().round(1).to_csv('datos/hf/historico_horario.csv.gz',compression='gzip')
log.write(f'total {len(A)} filas {A.index.min()} {A.index.max()}\n'+A.notna().sum().to_string()+'\n')
