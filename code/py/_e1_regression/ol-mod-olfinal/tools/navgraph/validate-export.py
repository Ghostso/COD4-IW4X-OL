"""Ingest a user-edited room graph into local review storage, never into gameplay."""
import argparse,datetime,hashlib,json,math,shutil
from pathlib import Path
H=Path(__file__).resolve().parent

def validate(g,b):
 for field in ['schema','map','room','baseGraphSha256','captureSha256','coordinateMeaning','base']:
  if g.get(field)!=b[field]:raise ValueError('Wrong '+field)
 if g.get('excludedNodes')!=b['excludedNodes']:raise ValueError('Excluded ledges changed')
 if not isinstance(g.get('nodes'),list) or not isinstance(g.get('edges'),list) or len(g['nodes'])>4096 or len(g['edges'])>16384:raise ValueError('Invalid graph size')
 def point(p):return isinstance(p,list) and len(p)==3 and all(type(v) in (int,float) and math.isfinite(v) and abs(v)<100000 for v in p)
 import re
 ids={};blocked={n['id'] for n in b['excludedNodes']}
 for n in g['nodes']:
  k=n.get('id');p=n.get('p')
  if not isinstance(k,str) or not re.fullmatch(r'local:[1-9]\d*',k) or k in ids or k in blocked or not point(p):raise ValueError('Invalid node')
  ids[k]=n
 seen=set();pairs=set()
 for e in g['edges']:
  ends=e.get('ends');path=e.get('path');k=e.get('id')
  if not isinstance(k,str) or k in seen or not isinstance(ends,list) or len(ends)!=2 or not all(type(x)==str and x in ids for x in ends) or ends[0]==ends[1] or tuple(sorted(ends)) in pairs:raise ValueError('Invalid edge')
  if not isinstance(path,list) or not 2<=len(path)<=20000 or not all(point(p) for p in path) or path[0]!=ids[ends[0]]['p'] or path[-1]!=ids[ends[1]]['p']:raise ValueError('Invalid corridor')
  if e.get('enabled') is not False or e.get('validation')!='pending-live-hull-floor-gates':raise ValueError('Unvalidated edge cannot be enabled')
  seen.add(k);pairs.add(tuple(sorted(ends)))
 return True

def ingest(path,out=None):
 b=json.loads((H/'room-v2-base.json').read_text(encoding='utf-8'));data=path.read_bytes()
 if len(data)>8000000:raise ValueError('File too large')
 g=json.loads(data);validate(g,b)
 # Do not accept any user-supplied assertion of native provenance for edits.
 be={e['id']:e for e in b['edges']};bn={n['id']:n for n in b['nodes']}
 for e in g['edges']:
  if e!=be.get(e['id']):e['evidence']='manual-proposal';e.pop('sampleRange',None)
 g['status']='draft-unvalidated'
 changes=dict(addedNodes=[n['id'] for n in g['nodes'] if n['id'] not in bn],removedNodes=[k for k in bn if k not in {n['id'] for n in g['nodes']}],movedNodes=[n['id'] for n in g['nodes'] if n['id'] in bn and n['p']!=bn[n['id']]['p']],addedEdges=[e['id'] for e in g['edges'] if e['id'] not in be],removedEdges=[k for k in be if k not in {e['id'] for e in g['edges']}],changedEdges=[e['id'] for e in g['edges'] if e['id'] in be and e!=be[e['id']]])
 folder=out or H/'imports'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True,exist_ok=False)
 (folder/'original.json').write_bytes(data);(folder/'review-graph.json').write_text(json.dumps(g,indent=2));receipt=dict(sourceSha256=hashlib.sha256(data).hexdigest(),baseGraphSha256=b['baseGraphSha256'],structuralValidation='PASS',collisionValidation='PENDING',installed=False,changes=changes)
 (folder/'receipt.json').write_text(json.dumps(receipt,indent=2));return folder,receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('file',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();folder,receipt=ingest(a.file,a.output);print(json.dumps(dict(folder=str(folder),**receipt),indent=2))
