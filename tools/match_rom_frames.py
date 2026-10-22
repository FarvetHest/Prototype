from pathlib import Path
import re,sys,json
from prepare_sprites import decode
import argparse,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);args=ap.parse_args()
project=Path(__file__).resolve().parents[1]
assert hashlib.sha256(args.asm.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
ls=args.asm.read_text(encoding='utf-8',errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}

def number(v):return int(v[1:],16)if v.startswith('$')else int(v)
def dat(name):
 out=bytearray()
 for j,l in enumerate(ls[labels[name]:]):
  if j and re.match(r'^\w+:',l):break
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if m:
   n={'b':1,'w':2,'l':4}[m[1]]
   for v in m[2].split(','):out.extend((number(v.strip())&((1<<(n*8))-1)).to_bytes(n,'big'))
 return out
art=dat('ArtUnc_Axel');print('Art bytes',len(art))
_,fpg=decode(args.data/'bk3_axel.fpg')
def normalize(points):
 x=min(x for x,y in points);y=min(y for x,y in points);return frozenset((px-x,py-y)for px,py in points)
fpgsets={id:normalize({(i%f['w'],i//f['w'])for i,v in enumerate(f['pixels'])if v})for id,f in fpg.items()if any(f['pixels'])}
def render(mapping,regs):
 d=dat(mapping.split('+')[0]);n=int.from_bytes(d[:2],'big')+1;assert len(d)>=6+n*5,(mapping,n,len(d))
 addr=((regs[0]&255)|((regs[1]&255)<<8)|((regs[2]&127)<<16))*2-0x50000;pts=set()
 for i in range(n):
  yy,size,hi,lo,xx=d[6+i*5:11+i*5];xx=xx if xx<128 else xx-256;yy=yy if yy<128 else yy-256
  attr=(hi<<8)|lo;tile=attr&2047;w=((size>>2)&3)+1;h=(size&3)+1
  for x in range(w*8):
   for y in range(h*8):
    sx=w*8-1-x if attr&2048 else x;sy=h*8-1-y if attr&4096 else y
    off=addr+(tile+(sx//8)*h+sy//8)*32+(sy%8)*4+(sx%8)//2
    if off<0 or off>=len(art):raise ValueError((mapping,addr,off))
    color=(art[off]>>(4 if sx%2==0 else 0))&15
    if color:pts.add((xx+x,yy+y))
 return normalize(pts)
ref=json.loads((project/'assets/bk3-reference.json').read_text());rows=[r for v in ref['scripts'].values()for r in v['frames']]
seen={};result=[]
for row in rows:
 if row['mapping']in seen:continue
 points=render(row['mapping'],row['art']);matches=[]
 flipped=normalize({(-x,y)for x,y in points})
 for id,pix in fpgsets.items():
  score=max(len(points&pix)/len(points|pix),len(flipped&pix)/len(flipped|pix));matches.append((score,id))
 matches.sort(reverse=True);seen[row['mapping']]=matches[0][1]
 result.append(dict(mapping=row['mapping'],fpg=matches[0][1],iou=matches[0][0],candidates=matches[:3]))
print('exact matches',sum(x['iou']==1 for x in result),'/',len(result));print([(x['mapping'],x['fpg'],round(x['iou'],3))for x in result]);(project/'assets/axel-rom-match.json').write_text(json.dumps(result,indent=2))
