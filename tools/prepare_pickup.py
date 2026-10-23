"""Exact BK3 Axel pickup pose, mapped to the established SoRR Axel palette.
Prepare vault-native.json first; this tool does not alter the combat scripts.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,json,re
from prepare_sprites import decode,png
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

vault=json.loads((project/'assets/vault-native.json').read_text());ref=json.loads((project/'assets/bk3-reference.json').read_text());mapping={0:0}
for row,id in zip(ref['scripts']['vault']['frames'],range(900,905)):
 v=vault['frames'][str(id)];pixels=bytes.fromhex(v['pixels']);px,py=v['pivot']
 for (x,y),c in render(row['mapping'],row['art']).items():
  x=-x-1;index=pixels[(y+py)*v['w']+x+px]
  if c in mapping:assert mapping[c]==index
  mapping[c]=index
pix={(-x-1,y):mapping[c] for (x,y),c in render('word_116EE8',[0x9550,0x966f,0x9703]).items()};x0=min(x for x,y in pix);y0=min(y for x,y in pix);w=max(x for x,y in pix)-x0+1;h=max(y for x,y in pix)-y0+1;data=bytearray(w*h)
for (x,y),c in pix.items():data[(y-y0)*w+x-x0]=c
v=dict(w=w,h=h,pivot=[-x0,-y0],pixels=data.hex(),title='BK3 DMA_Axel_ItemPickUp / word_116EE8')
report=dict(frames={'910':v},source_sha256=hashlib.sha256(args.asm.read_bytes()).hexdigest(),mapping='word_116EE8',art=[0x9550,0x966f,0x9703],source_ticks=12)
(project/'assets/pickup-native.json').write_text(json.dumps(report,indent=2))
pal,_=decode(args.data/'bk3_axel.fpg');png(project/'assets/pickup-preview.png',w,h,bytes(c for q in data for c in pal[q]));print('Pickup pose:',w,h,v['pivot'])
