"""Lluvia diaria histórica para evaluar su aporte al pronóstico de extracción.
HydroForecast solo expone 14 días de pluviómetros y totales anuales DHIME, así que para 2019–2026 se usa:
  1) CHIRPS v2.0 diario (0,05°), promedio areal, vía IRI Data Library.
  2) NASA POWER (PRECTOTCORR, ~0,5°) en puntos, como verificación independiente.
Áreas (lon_min, lon_max, lat_min, lat_max):
  cola   : entre Olaya (6,63 N) y la barrera (6,90 N), laderas que drenan directo al embalse.
  media  : cuenca media del Cauca desde La Pintada (5,74 N) hasta la barrera."""
import io, os, sys, time, urllib.request, pandas as pd
OUT = "../datos/lluvia"; os.makedirs(OUT, exist_ok=True)
INI, FIN = "1 Jan 2019", time.strftime("%d %b %Y", time.gmtime(time.time() - 5 * 86400))
AREAS = {"cola": (-76.00, -75.60, 6.55, 7.00), "media": (-76.10, -75.40, 5.70, 7.00)}
def get(url, tries=4, timeout=600):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "flotante-ituango"}), timeout=timeout) as r:
                return r.read().decode()
        except Exception as e:
            print("reintento", k + 1, e); time.sleep(20 * (k + 1))
    raise RuntimeError("sin respuesta: " + url[:120])
series = {}
for nombre, (x0, x1, y0, y1) in AREAS.items():
    for var in ["daily-improved"]:
        url = ("https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.%s/.global/.0p05/.prcp/"
               "X/%s/%s/RANGEEDGES/Y/%s/%s/RANGEEDGES/T/(%s)/(%s)/RANGEEDGES/%%5BX/Y%%5Daverage/T/exch/table:/1/:table/.csv"
               % (var, x0, x1, y0, y1, INI.replace(" ", "%20"), FIN.replace(" ", "%20")))
        try:
            txt = get(url); df = pd.read_csv(io.StringIO(txt)); print(nombre, df.shape, df.columns.tolist(), df.head(2).to_dict("records"))
            df.columns = ["T", "prcp"]
            df["fecha"] = pd.to_datetime(df["T"].astype(str).str.replace(r"^(\d{1,2}) (\w{3}) (\d{4}).*$", r"\1 \2 \3", regex=True), errors="coerce")
            series[f"chirps_{nombre}"] = df.dropna(subset=["fecha"]).set_index("fecha")["prcp"]
        except Exception as e:
            print("CHIRPS falló", nombre, e)
# NASA POWER en puntos (verificación)
PUNTOS = {"barrera": (6.90, -75.84), "olaya": (6.63, -75.81), "sabanalarga": (6.85, -75.81), "pintada": (5.74, -75.60)}
for k, (la, lo) in PUNTOS.items():
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=AG&longitude=%s&latitude=%s&start=20190101&end=%s&format=CSV&header=false"
           % (lo, la, time.strftime("%Y%m%d", time.gmtime(time.time() - 5 * 86400))))
    try:
        df = pd.read_csv(io.StringIO(get(url))); df["fecha"] = pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY))
        s = df.set_index("fecha")["PRECTOTCORR"].where(lambda v: v >= 0); series[f"power_{k}"] = s; print("POWER", k, len(s))
    except Exception as e:
        print("POWER falló", k, e)
if not series: sys.exit("sin datos de lluvia")
D = pd.DataFrame(series).sort_index(); D.index.name = "fecha"
D.round(2).to_csv(f"{OUT}/lluvia_diaria.csv"); print(D.describe().round(2))
