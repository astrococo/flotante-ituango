import pickle,re,sys,collections
from openpyxl.utils import coordinate_to_tuple,get_column_letter
D=pickle.load(open(sys.argv[1],'rb'));n=sys.argv[2];S=D[n];C=S['cells']
print('==',n,S['max'],'merged',S['merged'],'dv',S['dv'],'freeze',S['freeze'],'cf',S['cf'],'hidden cols',S['hidden_cols'],'hidden rows',S['hidden_rows'])
rows=collections.defaultdict(dict)
for k,c in C.items():
    r,cc=coordinate_to_tuple(k);rows[r][cc]=c
H=int(sys.argv[3]) if len(sys.argv)>3 else 10
for r in sorted(rows)[:H]:
    print(r,{get_column_letter(cc):(str(c['v'])[:40],(c['f'] or '')[:60]) for cc,c in sorted(rows[r].items())})
# patrones de fórmula por columna
def norm(f,r): return re.sub(r'(\$?[A-Z]{1,3}\$?)(\d+)',lambda m:m.group(1)+('R' if m.group(2)==str(r) else ('R'+('%+d'%(int(m.group(2))-r)) if not m.group(1).endswith('$') and abs(int(m.group(2))-r)<5 else m.group(2))),f)
pat=collections.defaultdict(collections.Counter)
for k,c in C.items():
    if c['f']:
        r,cc=coordinate_to_tuple(k);pat[get_column_letter(cc)][norm(c['f'],r)]+=1
for col in sorted(pat,key=lambda x:(len(x),x)):
    print('fórmulas',col,pat[col].most_common(4))
print('comentarios:')
for k,c in C.items():
    if c['com']: print(' ',k,repr(c['v'])[:30],'|',c['com'].replace('\n',' ')[:400])
