from pathlib import Path
import re,json,hashlib,struct
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);args=ap.parse_args();p=Path(__file__).resolve().parents[1];a=args.asm
assert hashlib.sha256(a.read_bytes()).hexdigest()=='30f9c07ff55b85dd53083fe9b0a828faa3fb4600a0ac54dfc5f2d432265da274'
s=a.read_text(errors='replace'); ls=s.splitlines(); labels={m[1]:i for i,l in enumerate(ls) if(m:=re.match(r'^(\w+):',l))}
def block(n):
 i=labels[n];j=i+1
 while j<len(ls) and not re.match(r'^\w+:',ls[j]):j+=1
 return '\n'.join(ls[i:j])
def num(v):return int(v[1:],16) if v.startswith('$') else int(v)
def data(n):
 out=bytearray()
 for typ,vals in re.findall(r'dc\.([bwl])\s+([^;\n]+)',block(n)):
  for v in vals.split(','):
   z={'b':1,'w':2,'l':4}[typ];out.extend((num(v.strip())&((1<<(z*8))-1)).to_bytes(z,'big'))
 return out
pal=data('Pal_Barbon')[2:]; assert len(pal)==32
palette=[]
for i in range(16):
 c=int.from_bytes(pal[i*2:i*2+2],'big');palette.append([((c>>0)&14)*255//14,((c>>4)&14)*255//14,((c>>8)&14)*255//14,255 if i else 0])
frames={}; cache={}; scripts={}
names=['word_1EB8E4','word_1EB916','word_1EB948','word_1EB97A','word_1EB9D0','word_1EB9DE','word_1EB9EC','word_1EB9FA','word_1EBA08','word_1EBA82','word_1EBAFC','word_1EBB0A','word_1EBB18','word_1EBB4A','word_1EBB58','word_1EBBD8','word_1EBC16','word_1EBD12','word_1EBD44','word_1EBD6A']
for name in names:
 b=block(name); rec=re.findall(r'dc\.w\s+(\$[0-9A-F]+|\d+)\s*\n\s*dc\.l\s+(\w+)\s*\n\s*dc\.w\s+\(\(\((\w+)/',b)
 count=num(re.search(r'dc\.w\s+(\$[0-9A-F]+|\d+)',b)[1]);assert len(rec)==count,(name,count,len(rec))
 rows=[]
 for ticks,mapping,art in rec:
  key=(mapping,art)
  if key not in cache:
   d=data(mapping);n=int.from_bytes(d[:2],'big')+1;assert len(d)==6+n*6,(mapping,n,len(d));tiles=data(art);pts={}
   for j in range(n):
    xflipped,x,y,size,hi,lo=d[6+j*6:12+j*6];x=x if x<128 else x-256;y=y if y<128 else y-256;attr=hi*256+lo;tile=attr&2047;w=((size>>2)&3)+1;h=(size&3)+1
    # The FIRST X belongs to flipped pieces; the SECOND X to the unflipped art.
    assert (xflipped if xflipped<128 else xflipped-256)==-x-w*8
    for xx in range(w*8):
     for yy in range(h*8):
      sx=w*8-1-xx if attr&2048 else xx;sy=h*8-1-yy if attr&4096 else yy;off=(tile+(sx//8)*h+sy//8)*32+(sy%8)*4+(sx%8)//2;assert off<len(tiles),(mapping,art,off,len(tiles));c=(tiles[off]>>(4 if sx%2==0 else 0))&15
      if c:pts[(x+xx,y+yy)]=c
   x0=min(x for x,y in pts);y0=min(y for x,y in pts);w=max(x for x,y in pts)-x0+1;h=max(y for x,y in pts)-y0+1;pix=bytearray(w*h)
   for (x,y),c in pts.items():pix[(y-y0)*w+x-x0]=c
   id=1000+len(cache);cache[key]=id;frames[str(id)]=dict(w=w,h=h,pivot=[-x0,-y0],pixels=pix.hex(),title='SoR2 '+mapping+' / '+art)
  rows.append(dict(ticks=num(ticks),fpg=cache[key],mapping=mapping,art=art))
 scripts[name]=rows
native=json.loads((p/'assets/enemy-native.json').read_text());native['barbon']=dict(palette=palette,palette_label='Pal_Barbon',cram=[int.from_bytes(pal[i:i+2],'big')for i in range(0,32,2)],frames=frames,source_art='SoR2 uncompressed per-frame Barbon art',source_sha256=hashlib.sha256(a.read_bytes()).hexdigest());(p/'assets/enemy-native.json').write_text(json.dumps(native,indent=2))
report=dict(source_file=a.name,source_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),repository='https://github.com/gsaurus/sor-disassemblies',commit='4dd719f3ed5c24c86deee616b56cea885e3113d7',scripts=scripts,profiles=list(data('byte_14E82')),collisions={n:list(data(n)) for n in ['byte_2A5C','byte_2A6C','byte_2A78']})
(p/'assets/barbon-source.json').write_text(json.dumps(report,indent=2))
# Source attack width is signed byte*2; vertical contact is a point at -height.
# Adapt the point to a one-pixel rectangle accepted by the Lite overlap routine.
boxes=[[0]*8]; sequences={}; kinds=['word_1EB8E4','word_1EB916','word_1EB9D0','word_1EB9FA','word_1EB9EC','word_1EBAFC','word_1EBB0A','word_1EBB18','word_1EBBD8','word_1EBC16','word_1EBD12','word_1EBD6A','word_1EBD44','word_1EB97A','word_1EBB58']
head=['/* Generated from pinned SoR2 listing; geometry adapted to Lite rectangles. */','#ifndef BARBON_DATA_H','#define BARBON_DATA_H']
for k,name in enumerate(kinds):
 rows=[];coll=report['collisions'].get({'word_1EBD12':'byte_2A5C','word_1EBD44':'byte_2A6C','word_1EBD6A':'byte_2A78'}.get(name,''),[])
 for j,r in enumerate(scripts[name]):
  id=damage=0
  if coll:
   width,height,damage,_=coll[j*4:j*4+4]
   if width or height:
    width=(width if width<128 else width-256)*2;height=height if height<128 else height-256
    # signed char width limit: original reach max112, safe.
    boxes.append([-max(width,0),abs(width),-height,1,min(width,0),abs(width),-height,1]);id=len(boxes)-1
  rows.append('{%d,%d,1,%d,%d}'%(r['ticks'],r['fpg'],id,damage))
 head.append('static const EnemyFrame barbon_%d[]={%s};'%(k,','.join(rows)))
head+=['static const EnemyFrame *const barbon_sequences[]={'+','.join('barbon_'+str(k) for k in range(len(kinds)))+'};','static const unsigned char barbon_sizes[]={'+','.join(str(len(scripts[n]))for n in kinds)+'};','static const signed char barbon_boxes[][8]={'+','.join('{'+','.join(map(str,b))+'}'for b in boxes)+'};', 'static const signed char barbon_hurt[8]={-20,40,-88,88,-20,40,-88,88};','#endif']
v=report['profiles'];head.insert(-1,'static const unsigned char barbon_profiles[6][32]={'+','.join('{'+','.join(map(str,v[j:j+32]))+'}'for j in range(0,192,32))+'};')
(p/'src/barbon_data.h').write_text('\n'.join(head)+'\n');print(len(frames),'native Barbon poses',len(report['profiles']),'profile bytes')

used={'Pal_Barbon','byte_14E82','byte_2A5C','byte_2A6C','byte_2A78'}|set(names)|{n for k in cache for n in k}
excerpt='; Extracted from pinned SoR2 listing; original label spelling preserved.\n'+'\n'.join(block(n)for n in sorted(used,key=lambda n:labels[n]))+'\n'
(p/'original/vendor/SOR2-Barbon-data.asm').write_text(excerpt)

(p/'original/vendor/SOR2-Barbon-code.asm').write_text('\n'.join(ls[labels['Obj_Barbon']:labels['Obj_Electra']])+'\n')
