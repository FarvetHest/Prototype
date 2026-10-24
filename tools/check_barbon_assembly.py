from pathlib import Path
import json,re,zlib,base64,hashlib
p=Path(__file__).resolve().parents[1]
n=json.loads((p/'assets/enemy-native.json').read_text())['barbon']['frames'];ref=json.loads((p/'assets/barbon-fpg-silhouettes.json').read_text())
def points(v):
 b=bytes.fromhex(v['pixels']);pts={(i%v['w'],i//v['w'])for i,c in enumerate(b)if c};return norm(pts)
def norm(s):
 x0=min(x for x,y in s);y0=min(y for x,y in s);return {(x-x0,y-y0)for x,y in s}
def iou(s,t):return len(s&t)/len(s|t)
scores={};targets={}
for k,r in ref['frames'].items():
 mask=zlib.decompress(base64.b64decode(r['mask']));t={(i%r['w'],i//r['w'])for i,v in enumerate(mask)if v};targets[k]=t;s=points(n[k]);s=norm({(-x if r['flip_x']else x,-y if r['flip_y']else y)for x,y in s});scores[k]=iou(s,t)
ls=(p/'original/vendor/SOR2-Barbon-data.asm').read_text().splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}
def data(name):
 out=bytearray();j=labels[name]
 for i,l in enumerate(ls[j:]):
  if i and re.match(r'^\w+:',l):break
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if m:
   size={'b':1,'w':2,'l':4}[m[1]]
   for v in m[2].split(','):
    v=v.strip();n=int(v[1:],16)if v.startswith('$')else int(v);out.extend((n&((1<<(size*8))-1)).to_bytes(size,'big'))
 return out
# Reconstruct the actual former defect independently from the pinned mapping/art.
d=data('word_15F6FA');art=data('byte_14FDBA');bad=set();pairs=True
for j in range(int.from_bytes(d[:2],'big')+1):
 xf,x,y,size,hi,lo=d[6+j*6:12+j*6];xf=xf if xf<128 else xf-256;x=x if x<128 else x-256;y=y if y<128 else y-256;attr=hi*256+lo;w=((size>>2)&3)+1;h=(size&3)+1;pairs &= xf==-x-w*8
 for xx in range(w*8):
  for yy in range(h*8):
   sx=w*8-1-xx if attr&2048 else xx;sy=h*8-1-yy if attr&4096 else yy;off=((attr&2047)+(sx//8)*h+sy//8)*32+(sy%8)*4+(sx%8)//2;c=(art[off]>>(4 if sx%2==0 else 0))&15
   if c:bad.add((-xf-xx-1,y+yy))
bad_score=iou(norm(bad),targets['1000'])
checks=dict(all_36_independent_SoRR_silhouettes=all(scores[k]>=r['minimum_iou']for k,r in ref['frames'].items()),idle_walk_at_least_95_percent=all(scores[str(k)]>=.95 for k in range(1000,1005)),attacks_at_least_85_percent=all(scores[str(k)]>=.85 for k in range(1024,1036)),throw_rotation_reference_exact=scores['1022']==scores['1023']==1,former_split_body_bug_rejected=bad_score<.95,source_X_columns_are_mirror_pairs=pairs)
r=dict(checks=checks,scores=scores,former_bug_iou=bad_score,reference_FPG_sha256=ref['sha256'],note='Independent SoRR reference silhouettes; source SoR2 art differs slightly. This rejects the former internally mirrored fragment assembly, rather than comparing the renderer only with its own generated output.')
(p/'test-results/barbon-assembly-tests.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert all(checks.values())
