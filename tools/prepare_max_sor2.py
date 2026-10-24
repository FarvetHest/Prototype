"""Extract Max's original animation, collision and sprite records from pinned SoR2.
No guessed Axel-to-Max attack aliases. Coordinates are the normal (second) X.
"""
from pathlib import Path
import re,json,hashlib,argparse,struct
from prepare_sprites import png
p=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);a=ap.parse_args()
raw=a.asm.read_bytes();assert hashlib.sha256(raw).hexdigest()=='30f9c07ff55b85dd53083fe9b0a828faa3fb4600a0ac54dfc5f2d432265da274'
ls=raw.decode(errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}
def block(n):
 i=labels[n];j=i+1
 while j<len(ls)and not re.match(r'^\w+:',ls[j]):j+=1
 return '\n'.join(ls[i:j])
def num(v):return int(v[1:],16)if v.startswith('$')else int(v)
def data(n,size=None):
 out=bytearray()
 lines=ls[labels[n]:]if size else block(n).splitlines()
 for l in lines:
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if not m:continue
  z={'b':1,'w':2,'l':4}[m[1]]
  for v in m[2].split(','):
   v=v.strip();out+=(num(v)&((1<<(z*8))-1)).to_bytes(z,'big')
  if size and len(out)>=size:return out[:size]
 return out
def signed(v):return v-256 if v&128 else v
pal=data('word_FEFE',32);palette=[tuple(((int.from_bytes(pal[i*2:i*2+2],'big')>>s)&14)*255//14 for s in(0,4,8))+(255 if i else 0,)for i in range(16)]+[(0,0,0,0)]*240
cache={};poses={};scripts={};used={'word_FEFE','AttackCollision_Max','LoadCues_Max'}
for anim in list(range(0,0x54,2))+[0x62]:
 table='LoadCues_Max'if not anim else'word_%X'%(0xfa4b4+anim)
 target=re.search(r'dc\.w\s+(\w+)-',block(table))[1];used|={table,target}
 records=re.findall(r'dc\.w\s+(\$[\dA-F]+|\d+)\s*\n\s*dc\.l\s+(\w+)\s*\n\s*dc\.w\s+\(\(\((\w+)/',block(target))
 assert len(records)==num(re.search(r'dc\.w\s+(\$[\dA-F]+|\d+)',block(target))[1]),target
 coll=[]
 if anim>=0x30:
  ct='AttackCollision_Max'if anim==0x30 else'word_%X'%(0x2400+anim-0x30)
  m=re.search(r'dc\.w\s+(byte_\w+)-',block(ct)) if ct in labels else None
  if m:used.add(m[1]);coll=list(data(m[1]))
 rows=[]
 for j,(ticks,mapping,art)in enumerate(records):
  key=(mapping,art);used|={mapping,art}
  if key not in cache:
   h=data(mapping,6);n=int.from_bytes(h[:2],'big')+1;d=data(mapping,6+n*6);assert len(d)==6+n*6
   pieces=[d[6+k*6:12+k*6]for k in range(n)]
   needed=max((((b[4]*256+b[5])&2047)+(((b[3]>>2)&3)+1)*((b[3]&3)+1))*32 for b in pieces)
   tiles=data(art,needed);pts={}
   for xf,x,y,size,hi,lo in pieces:
    x=signed(x);y=signed(y);w=((size>>2)&3)+1;hh=(size&3)+1;attr=hi*256+lo
    assert signed(xf)==-x-w*8,(mapping,x,xf)
    for yy in range(hh*8):
     for xx in range(w*8):
      sx=w*8-1-xx if attr&2048 else xx;sy=hh*8-1-yy if attr&4096 else yy
      off=((attr&2047)+(sx//8)*hh+sy//8)*32+(sy%8)*4+(sx%8)//2;c=(tiles[off]>>(4 if sx%2==0 else 0))&15
      if c:pts[x+xx,y+yy]=c
   x0=min(x for x,y in pts);y0=min(y for x,y in pts);w=max(x for x,y in pts)-x0+1;hh=max(y for x,y in pts)-y0+1;pix=bytearray(w*hh)
   for(x,y),c in pts.items():pix[(y-y0)*w+x-x0]=c
   fid=1000+len(cache);cache[key]=fid;poses[fid]=dict(id=fid,w=w,h=hh,px=-x0,py=-y0,pixels=pix,mapping=mapping,art=art)
  ci=len(records)-1-j
  collision=coll[ci*4:ci*4+4]if coll else[0,0,0,0];assert len(collision)==4,(hex(anim),j,len(coll))
  rows.append(dict(ticks=num(ticks),fpg=cache[key],width=signed(collision[0])*2,height=signed(collision[1]),damage=collision[2],sound=collision[3],mapping=mapping,art=art))
 scripts[anim]=rows
# Two pages are expected; allocate only RAM and assert bounds at extraction time.
atlas=bytearray(512*512*4);x=y=1;row=0
for e in poses.values():
 if x+e['w']+1>512:x=1;y+=row+2;row=0
 if y//512!=(y+e['h'])//512:x=1;y=(y//512+1)*512+1;row=0
 assert y+e['h']<2048
 e.update(u=x,v=y)
 for sy in range(e['h']):atlas[(y+sy)*512+x:(y+sy)*512+x+e['w']]=e['pixels'][sy*e['w']:(sy+1)*e['w']]
 x+=e['w']+2;row=max(row,e['h'])
pages=(y+row+511)//512;atlas=atlas[:pages*262144];sw=bytearray()
for by in range(0,pages*512,8):
 for bx in range(0,512,16):
  for dy in range(8):sw+=atlas[(by+dy)*512+bx:(by+dy)*512+bx+16]
(p/'assets/max.t8').write_bytes(sw)
head=['/* Generated from original SoR2 Max maps/art; normal X, column-major tiles. */','#ifndef MAX_DATA_H','#define MAX_DATA_H',f'#define MAX_TEXTURE_BYTES {len(sw)}','extern const unsigned char max_atlas[];','static const unsigned __attribute__((aligned(16))) max_palette[256]={'+','.join(hex(r|(g<<8)|(b<<16)|(a<<24))+'u'for r,g,b,a in palette)+'};','static const SpriteFrame max_frames[]={']
head+=['{6,'+','.join(str(e[k])for k in['id','u','v','w','h','px','py'])+'},'for e in poses.values()]
# Existing body/held interfaces still publish Axel pose IDs; map only presentation fallbacks.
fallback={1:0,2:0,3:0,4:0,148:0x12,47:0x12,48:0x14,49:0x14,50:0x16,51:0x18,910:0x1c,920:0x1a,921:0x1a,922:0x10,923:0x10}
head+=['};','static const unsigned short max_aliases[][2]={']+['{%d,%d},'%(k,scripts[v][0]['fpg'])for k,v in fallback.items()]+['};','#endif']
(p/'src/max_data.h').write_text('\n'.join(head)+'\n')
dh=['/* Generated original ticks, per-frame reach/height/damage/sound. */','#ifndef MAX_SOR2_DATA_H','#define MAX_SOR2_DATA_H','typedef struct {short ticks,fpg,width,height;unsigned char damage,sound;} MaxFrame;']
for anim,rows in scripts.items():dh.append('static const MaxFrame max_seq_%02x[]={%s};'%(anim,','.join('{%d,%d,%d,%d,%d,%d}'%tuple(r[k]for k in['ticks','fpg','width','height','damage','sound'])for r in rows)))
dh+=['static const MaxFrame *const max_sequences[50]={'+','.join('max_seq_%02x'%i if i in scripts else'0'for i in range(0,100,2))+'};','static const unsigned char max_counts[50]={'+','.join(str(len(scripts[i]))if i in scripts else'0'for i in range(0,100,2))+'};']
for name in['word_D276','word_D640','word_D266']:
 blob=data(name,24 if name=='word_D266' else 48);values=struct.unpack('>'+str(len(blob)//2)+'h',blob);dh.append('static const short max_%s[]={%s};'%(name,','.join(map(str,values))));used.add(name)
dh+=['#endif'];(p/'src/max_sor2_data.h').write_text('\n'.join(dh)+'\n')
manifest=dict(source_sha256=hashlib.sha256(raw).hexdigest(),commit='4dd719f3ed5c24c86deee616b56cea885e3113d7',scripts=scripts,palette=palette,atlas_pages=pages,atlas_bytes=len(sw),atlas_sha256=hashlib.sha256(sw).hexdigest(),frame_count=len(poses),frames=[dict({k:v for k,v in e.items()if k!='pixels'},pixel_sha256=hashlib.sha256(e['pixels']).hexdigest())for e in poses.values()])
(p/'assets/max-sor2-source.json').write_text(json.dumps(manifest,indent=2))
(p/'assets/max-manifest.json').write_text(json.dumps(manifest,indent=2))
cw=1024;ch=((len(poses)+9)//10)*128;rgba=bytearray(bytes((24,24,32,255))*(cw*ch))
for j,e in enumerate(poses.values()):
 ox=(j%10)*100+50-e['px'];oy=(j//10)*128+112-e['py']
 for sy in range(e['h']):
  for sx in range(e['w']):
   c=e['pixels'][sy*e['w']+sx];xx=ox+sx;yy=oy+sy
   if c and 0<=xx<cw and 0<=yy<ch:rgba[(yy*cw+xx)*4:(yy*cw+xx)*4+4]=bytes(palette[c])
png(p/'assets/max-contact.png',cw,ch,rgba)
(p/'original/vendor/SOR2-Max-data.asm').write_text('; Pinned source records used by prepare_max_sor2.py\n'+'\n'.join(block(n)for n in sorted(used,key=lambda n:labels[n]))+'\n')
print('Max original:',len(poses),'poses,',len(scripts),'scripts,',pages,'RAM pages')
