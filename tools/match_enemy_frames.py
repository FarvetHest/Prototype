"""Reconstruct pinned BK3 enemy poses and compare local FPG silhouettes."""
import argparse,re,json,hashlib
from pathlib import Path
from prepare_sprites import decode
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);a=ap.parse_args()
p=Path(__file__).resolve().parents[1]
assert hashlib.sha256(a.asm.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
ls=a.asm.read_text(encoding='utf-8',errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}
def num(v):
 if '+'in v:return sum(num(x)for x in v.split('+'))
 if v.startswith(('word_','byte_','loc_')):return int(v.split('_')[1],16)
 return int(v[1:],16)if v.startswith('$')else int(v)
def tokens(name,n=None):
 out=[]
 for i,l in enumerate(ls[labels[name]:]):
  if i and n is None and re.match(r'^\w+:',l):break
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if m:out.extend((m[1],v.strip())for v in m[2].split(','))
  if n and len(out)>=n:return out[:n]
 return out
def dat(name):return b''.join((num(v)&((1<<(8*{'b':1,'w':2,'l':4}[k]))-1)).to_bytes({'b':1,'w':2,'l':4}[k],'big')for k,v in tokens(name))
def nemesis(raw):
 header=int.from_bytes(raw[:2],'big');target=(header&32767)*64;pos=2;table={};color=0
 while raw[pos]!=255:
  code=raw[pos];pos+=1
  if code&128:color=code&15;continue
  length=code&15;run=((code>>4)&7)+1;bits=raw[pos];pos+=1;table[(length,bits)]=(run,color)
 pos+=1;cursor=pos*8
 def bits(n):
  nonlocal cursor
  val=0
  for _ in range(n):val=(val<<1)|((raw[cursor//8]>>(7-cursor%8))&1);cursor+=1
  return val
 pixels=[]
 while len(pixels)<target:
  code=0
  for length in range(1,9):
   code=(code<<1)|bits(1)
   if length==6 and code==63:run=bits(3)+1;color=bits(4);break
   if (length,code)in table:run,color=table[length,code];break
  else:raise ValueError('Invalid Nemesis code')
  pixels.extend([color]*run)
 assert len(pixels)==target
 if header&32768:
  for i in range(8,len(pixels)):pixels[i]^=pixels[i-8]
 return bytes(pixels)
art=nemesis(dat('ArtNem_GarciaDonovan'));assert len(art)==405*64
def norm(pts):
 x0=min(x for x,y in pts);y0=min(y for x,y in pts);return frozenset((x-x0,y-y0)for x,y in pts)
def render_pixels(label):
 raw=dat(label);n=int.from_bytes(raw[:2],'big')+1;assert len(raw)>=6+n*5
 pts={}
 for i in range(n):
  yy,size,hi,lo,xx=raw[6+i*5:11+i*5];yy=yy if yy<128 else yy-256;xx=xx if xx<128 else xx-256
  attr=hi*256+lo;tile=attr&2047;w=((size>>2)&3)+1;h=(size&3)+1
  for x in range(w*8):
   for y in range(h*8):
    sx=w*8-1-x if attr&2048 else x;sy=h*8-1-y if attr&4096 else y
    off=(tile+(sx//8)*h+sy//8)*64+(sy%8)*8+sx%8
    assert off<len(art),(label,tile,off)
    if art[off] and (xx+x,yy+y)not in pts:pts[xx+x,yy+y]=art[off]
 return pts
def render(label):return norm(render_pixels(label))
sets={'garcia':('galsia',{'idle':'word_202E3C','walk':'word_202E5E','held':'word_202E8A','hurt2':'word_202E94','hurt':'word_202EE6','flight':'word_202F38','floor':'word_202F4A','getup':'word_202F54','front':'word_202FD6','back':'word_203000','jab':'word_203158'}),'donovan':('donovan',{'idle':'word_203796','walk':'word_2037B8','held':'word_2037DA','hurt2':'word_2037E4','hurt':'word_203836','flight':'word_203888','floor':'word_20389A','getup':'word_2038A4','front':'word_203914','back':'word_20393E','jab':'word_203A96','uppercut':'word_203AC8','kick':'word_203AFA'})}
result={}
for family,(file,entries)in sets.items():
 _,fpg=decode(a.data/(file+'.fpg'));shapes={i:norm({(k%f['w'],k//f['w'])for k,v in enumerate(f['pixels'])if v})for i,f in fpg.items()if any(f['pixels'])};scripts={}
 for name,label in entries.items():
  n=num(tokens(label,1)[0][1]);rows=tokens(label,1+n*4)[1:];frames=[]
  for i in range(n):
   row=rows[i*4:i*4+4];mapping=row[1][1];pts=render(mapping);flipped=norm({(-x,y)for x,y in pts});scores=[]
   for id,shape in shapes.items():
    for flip,compare in [(0,pts),(1,flipped)]:scores.append((len(compare&shape)/len(compare|shape),id,flip))
   scores.sort(reverse=True);score,id,flip=scores[0]
   frames.append(dict(ticks=num(row[0][1]),mapping=mapping,hurt=num(tokens(mapping,2)[1][1]),collision=num(row[2][1]),damage=num(row[3][1]),fpg=id,flip=flip,iou=score))
  scripts[name]=dict(label=label,frames=frames)
  print(family,name,[(f['fpg'],round(f['iou'],3),f['flip'])for f in frames])
 result[family]=scripts
(p/'assets/enemy-rom-match.json').write_text(json.dumps(result,indent=2))

# Exact source geometry, with SoRR colors calibrated from overlapping matched pixels.
from collections import Counter
native={}
for family,(file,entries)in sets.items():
 palette,fpg=decode(a.data/(file+'.fpg'));votes=[Counter()for _ in range(16)];seen=set()
 for script in result[family].values():
  for f in script['frames']:
   if f['iou']<.8 or f['mapping']in seen:continue
   seen.add(f['mapping']);pix=render_pixels(f['mapping']);fr=fpg[f['fpg']]
   x0=min(x for x,y in pix);y0=min(y for x,y in pix)
   fp={(k%fr['w'],k//fr['w']):v for k,v in enumerate(fr['pixels'])if v};fx=min(x for x,y in fp);fy=min(y for x,y in fp)
   for (x,y),v in pix.items():
    idx=fp.get((x-x0+fx,y-y0+fy),0)
    if idx:votes[v][idx]+=1
 colors=[(0,0,0,0)]+[palette[v.most_common(1)[0][0]]if v else(255,0,255,255)for v in votes[1:]]
 frames={};mapping_ids={label:1000+i for i,label in enumerate(sorted({f['mapping']for sc in result[family].values()for f in sc['frames']}))}
 for label,id in mapping_ids.items():
  pix=render_pixels(label);x0=min(x for x,y in pix);y0=min(y for x,y in pix);w=max(x for x,y in pix)-x0+1;h=max(y for x,y in pix)-y0+1
  data=bytearray(w*h)
  for(x,y),v in pix.items():data[(y-y0)*w+x-x0]=v
  frames[id]=dict(w=w,h=h,pivot=[-x0,-y0],pixels=data.hex(),title=label)
 for sc in result[family].values():
  for f in sc['frames']:f['sorr_fpg']=f['fpg'];f['fpg']=mapping_ids[f['mapping']];f['flip']=0
 native[file]=dict(palette=colors,frames=frames,source_art='ArtNem_GarciaDonovan',source_sha256=hashlib.sha256(a.asm.read_bytes()).hexdigest(),color_note='Source pixels and pivots; colors calibrated from local SoRR FPG, not original CRAM')
(p/'assets/enemy-rom-match.json').write_text(json.dumps(result,indent=2))
(p/'assets/enemy-native.json').write_text(json.dumps(native))
print('Native poses', {k:len(v['frames'])for k,v in native.items()})
