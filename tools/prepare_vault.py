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
 addr=((regs[0]&255)|((regs[1]&255)<<8)|((regs[2]&127)<<16))*2-0x50000;pts={}
 for i in range(n):
  yy,size,hi,lo,xx=d[6+i*5:11+i*5];xx=xx if xx<128 else xx-256;yy=yy if yy<128 else yy-256
  attr=(hi<<8)|lo;tile=attr&2047;w=((size>>2)&3)+1;h=(size&3)+1
  for x in range(w*8):
   for y in range(h*8):
    sx=w*8-1-x if attr&2048 else x;sy=h*8-1-y if attr&4096 else y
    off=addr+(tile+(sx//8)*h+sy//8)*32+(sy%8)*4+(sx%8)//2
    if off<0 or off>=len(art):raise ValueError((mapping,addr,off))
    color=(art[off]>>(4 if sx%2==0 else 0))&15
    if color:pts[(xx+x,yy+y)]=color
 return pts
from collections import Counter
ref=json.loads((project/'assets/bk3-reference.json').read_text());palette,fpg=decode(args.data/'bk3_axel.fpg');votes=[Counter() for _ in range(16)];poses=[]
for row,id in zip(ref['scripts']['vault']['frames'],[150,151,249,151,150]):
 # BK3 base pose faces left; Lite family0 uses right-facing base art.
 pix={(-x-1,y):v for (x,y),v in render(row['mapping'],row['art']).items()};x0=min(x for x,y in pix);y0=min(y for x,y in pix)
 fr=fpg[id];fp={(k%fr['w'],k//fr['w']):v for k,v in enumerate(fr['pixels'])if v};fx=min(x for x,y in fp);fy=min(y for x,y in fp);w=max(x for x,y in pix)-x0+1
 normal=normalize(pix);base=normalize(fp);mirrored=normalize({(-x,y)for x,y in fp});flip=normal!=base
 assert normal==(mirrored if flip else base),row['mapping']
 for (x,y),v in pix.items():
  sx=w-1-(x-x0) if flip else x-x0;votes[v][fp[sx+fx,y-y0+fy]]+=1
 poses.append((row,pix,x0,y0))
indices=[0]+[v.most_common(1)[0][0] if v else 0 for v in votes[1:]];result={}
for i,(row,pix,x0,y0) in enumerate(poses):
 w=max(x for x,y in pix)-x0+1;h=max(y for x,y in pix)-y0+1;data=bytearray(w*h)
 for (x,y),v in pix.items():data[(y-y0)*w+x-x0]=indices[v]
 result[900+i]=dict(w=w,h=h,pivot=[-x0,-y0],pixels=data.hex(),title=row['mapping'])
report=dict(frames=result,source_sha256=ref['source_sha256'],source_art='ArtUnc_Axel',orientation='raw mappings mirrored to right-facing Lite family0 convention',palette_note='Source4bit indices fitted to the exact matching local SoRR poses',mapping_ids={row['mapping']:900+i for i,(row,*_)in enumerate(poses)})
(project/'assets/vault-native.json').write_text(json.dumps(report,indent=2));print('Vault mappings:',[(k,v['w'],v['h'],v['pivot']) for k,v in result.items()])
