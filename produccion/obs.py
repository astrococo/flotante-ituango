import re,unicodedata
def norm(s): return unicodedata.normalize('NFKD',str(s).lower()).encode('ascii','ignore').decode()
CATS=[('vacaciones',r'vacacion'),('festivo',r'festiv|semana santa|navidad|ano nuevo|eucarist|celebracion|dia del conductor'),
 ('descanso',r'descans|fin de semana|domingo'),('sin_reporte',r'no se realizo reporte|no se reporto|sin reporte'),
 ('covid',r'aislamiento|covid|cuarentena|confinamiento obligatorio|pandemia'),
 ('orden_publico',r'orden publico|paro |bloqueo|protesta|asonada'),
 ('clima',r'lluvia|tormenta|aguacero|clima|creciente|tempestad|rayo|niebla|electrica'),
 ('mancha',r'mancha|no hay material|poco material|sin material|escaso material|no se evidencia material|ausencia de material|baja presencia|no habia material|disponibilidad de material|localizacion'),
 ('barreras',r'barrera|camandula|anclaje'),
 ('equipos',r'varad|danad|dano|averi|mantenimiento de (?:la |las |los )?(?:volqueta|equipo|maquina|retro|bulldozer|excavadora)|bateria|taller|repar|llanta|mecanic|falla'),
 ('combustible',r'combustible|acpm|isotanque'),
 ('capacitacion',r'capacitaci|sst|arl|charla|reunion|induccion|simulacro'),
 ('contrato',r'contrato|documentacion|firma'),
 ('via_acopio',r'via|carreteable|botadero|acopio lleno|adecuacion'),
 ('composicion',r'composicion|mezcla|mayor representacion'),
 ('contingencia',r'contingencia|derrumbe|tunel|emergencia|evacuacion')]
def categorias(s):
    t=norm(s);return [c for c,p in CATS if re.search(p,t)]
def hora_inicio(s):
    t=norm(s)
    m=re.search(r'inici\w*[^0-9]{0,40}?(\d{1,2})\s*[:.;]\s*(\d{2})\d*(?::\d{2})?\s*([ap])?',t)
    if not m: return None
    h=int(m[1]);mi=int(m[2]) if int(m[2])<60 else int(str(m[2])[:1])*10
    if m[3]=='p' and h<12: h+=12
    if h>18 or h<4: return None
    return h+mi/60
