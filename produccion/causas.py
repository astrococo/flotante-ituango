import re
from obs import norm
# prioridad: la primera que coincide
REGLAS=[
 ('externa', r'aislamiento|covid|cuarentena|orden publico|paro armado|paro nacional|grupos al margen|restriccion dada por el area de seguridad|derrumbe|tunel de chiri|contingencia|evacuacion|emergencia'),
 ('programada', r'vacacion|descans|fin de semana|festiv|semana santa|viernes santo|jueves santo|navidad|ano nuevo|eleccion|electoral|capacitaci|\bsst\b|\barl\b|induccion|charla|eucarist|dia del conductor|administrativ|programacion de otras actividades|visita las centrales|actividad complementaria|examenes medicos|reunion|simulacro|actividades conexas'),
 ('disponibilidad', r'viento|desabastec|mancha|localizacion del material|ubicacion del material|no hay material|poco material|baja presencia|sin material|caudal|creciente|nivel(es)? del (rio|embalse)|perdida de la piscina|material muy distante|no fue posible confinar|no logro confinar'),
 ('operativa', r'barrera|camandula|confinamiento|lastre|piscina|equipo|maquin|volqueta|retro|excavadora|bulldozer|varad|mantenimiento|repar|combustible|isotanque|via|carreteable|acopio|residuos|astillado|traslado|recoleccion|limpieza|lancha|embarcacion|logistic|aprestamiento'),
 ('sin_reporte', r'no se realizo reporte|no se reporto|sin reporte'),
]
def causa(texto):
    t=norm(texto or '')
    if not t.strip(' |'): return 'sin_texto'
    for c,p in REGLAS:
        if re.search(p,t): return c
    return 'no_especificada'
