"""Export original BK3 actors, complete animation tables and sparse AI program bank.
Input bytes are recovered from the pinned local IDA database, not downloaded ROMs.
The native runtime executes AI code only; rendering, stage and player stay PSP C/sceGu.
"""
from pathlib import Path
import argparse,struct,json,re,hashlib,sys
from prepare_sprites import png
p=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--rom',type=Path,required=True);ap.add_argument('--names',type=Path,required=True);a=ap.parse_args()
r=a.rom.read_bytes();names=json.loads(a.names.read_text());rev={v:k for k,v in names.items()}
assert len(r)==0x300000 and hashlib.sha256(r).hexdigest()=='70d40c55c40a1db40be7e5845aaa60a39b123362b8c48a21cec7ebe6f6d1cd60'
asm=(p/'original/vendor/BK3.asm').read_text(errors='replace');assert hashlib.sha256((p/'original/vendor/BK3.asm').read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
u16=lambda o:struct.unpack_from('>H',r,o)[0];s16=lambda o:struct.unpack_from('>h',r,o)[0];u32=lambda o:struct.unpack_from('>I',r,o)[0]
def nemesis(o):
 header=u16(o);target=(header&32767)*64;pos=o+2;table={};color=0
 while r[pos]!=255:
  code=r[pos];pos+=1
  if code&128:color=code&15;continue
  length=code&15;run=((code>>4)&7)+1;bits=r[pos];pos+=1;table[length,bits]=(run,color)
 pos+=1;cursor=pos*8
 def bits(n):
  nonlocal cursor
  val=0
  for _ in range(n):val=(val<<1)|((r[cursor//8]>>(7-cursor%8))&1);cursor+=1
  return val
 px=[]
 while len(px)<target:
  code=0
  for length in range(1,9):
   code=code*2+bits(1)
   if length==6 and code==63:run=bits(3)+1;color=bits(4);break
   if (length,code)in table:run,color=table[length,code];break
  else:raise ValueError('Nemesis '+hex(o))
  px.extend([color]*run)
 assert len(px)==target
 if header&32768:
  for i in range(8,len(px)):px[i]^=px[i-8]
 return bytes(px)
artlabels={14:'ArtNem_GarciaDonovan',16:'ArtNem_GarciaDonovan',18:'ArtNem_Scarab',20:'ArtNem_BikeStorm',22:'ArtNem_Dwight',24:'ArtNem_PRobot',26:'ArtNem_BikeStorm2',28:'ArtNem_Electra',30:'ArtNem_GoldieZack',32:'ArtNem_GoldieZack',34:'ArtNem_Chiba',36:'ArtNem_Chiba',38:'ArtNem_Chiba',40:'ArtNem_MacLeod',42:'ArtNem_MacLeod',44:'ArtNem_MacLeod',46:'ArtNem_Soozie',48:'ArtNem_Tiger',50:'ArtNem_RobotX',52:'ArtNem_DononvanBulldozer',56:'ArtNem_RobotX',60:'ArtNem_MonaLisa',68:'ArtNem_Jet',70:'ArtNem_Rocket',76:'ArtNem_Bruce',0x8a:'ArtNem_BikeStorm',0x90:'ArtNem_MonaLisa',0x94:'ArtNem_RobotX1',0x96:'ArtNem_RobotX1',0x98:'ArtNem_RobotX1',0x9a:'ArtNem_RobotX2',0x9c:'ArtNem_RobotX2'}
# Source ELC VDP placements are relative to each object's base tile.
# Bike 3000 + rider 4000; crashed bike 3000 + rider 4C00.
# Rocket1 3000, Rocket 4000, Jet 6340. RobotX's second phase is
# decompressed at FF6D00 relative to FF2000 (packed offset 4D00).
composites={
 'storm':[(0,'ArtNem_Bike'),(0x2000,'ArtNem_BikeStorm')],
 'storm2':[(0,'ArtNem_BikeCrash'),(0x3800,'ArtNem_BikeStorm2')],
 'jet':[(0,'ArtNem_Rocket1'),(0x2000,'ArtNem_Rocket'),(0x6680,'ArtNem_Jet')],
 'rocket':[(0,'ArtNem_Rocket'),(0x4680,'ArtNem_Jet')],
 'robotx':[(0,'ArtNem_RobotX1'),(0x8c0,'ArtNem_RobotX'),(0xa2c0,'ArtNem_RobotX2')],
}
for oid in [0x14]:artlabels[oid]='storm'
for oid in [0x1a,0x8a]:artlabels[oid]='storm2'
artlabels[0x44]='jet';artlabels[0x46]='rocket'
for oid in [0x32,0x38,0x94,0x96,0x98,0x9a,0x9c]:artlabels[oid]='robotx'
artlabels[0x40]=artlabels[0x92]='ArtNem_Yamato'
artlabels[0x42]='ArtNem_ShivaGeneralDisgiuse'
artcache={}
def art(name):
 if name not in artcache:
  if name in composites:
   parts=[(off,art(label))for off,label in composites[name]]
   buf=bytearray(max(off+len(px)for off,px in parts))
   for off,px in parts:buf[off:off+len(px)]=px
   artcache[name]=bytes(buf)
  else:artcache[name]=nemesis(names[name])
 return artcache[name]
# Reproduce the fixed VRAM art used by weapons and projectile mappings.
static=bytearray(2048*64)
base=names['dword_22AC'] if 'dword_22AC'in names else 0x22ac
for ix in [3,4,5,6,7,8,9,10,11,12,13,14,15,0x1e,0x1f]:
 cmd=u32(base+(ix-1)*8);src=u32(base+(ix-1)*8+4);addr=((cmd>>16)&0x3fff)|((cmd&3)<<14);px=nemesis(src);start=addr//32*64;static[start:start+len(px)]=px
# Definitions stay indexed by original ObjID, including colour/weapon variants.
ids=list(range(0xe,0x4e,2))+[0x8a,0x8e,0x90,0x92,0x94,0x96,0x98,0x9a,0x9c]+[0x58,0x5a,0x5c,0x5e,0x60,0x62,0x64,0x66,0x128,0x12a,0x12c,0x12e,0x9e,0xa0]
actors=[];poses={};skipped=[];invalid=[];sequences=[]
# Palette words as source default; per-object runtime LoadPalette can override them.
pal=[u16(names['Pal_MainPal']+i*2)for i in range(16)]
def render(mapping,rawart,compressed):
 count=u16(mapping)+1
 if not(0<count<160):raise ValueError('mapping pieces '+hex(mapping))
 pts={}
 for k in range(count):
  yy,size,hi,lo,xx=r[mapping+6+k*5:mapping+11+k*5];x=xx-256 if xx&128 else xx;y=yy-256 if yy&128 else yy;attr=hi*256+lo;w=((size>>2)&3)+1;h=(size&3)+1
  for iy in range(h*8):
   for ix in range(w*8):
    sx=w*8-1-ix if attr&2048 else ix;sy=h*8-1-iy if attr&4096 else iy;tile=(attr&2047)+(sx//8)*h+sy//8
    if rawart:
     off=rawart+tile*32+(sy%8)*4+(sx%8)//2
     if off>=len(r):raise ValueError('raw tile bound')
     c=(r[off]>>(0 if sx&1 else 4))&15
    else:
     off=tile*64+(sy%8)*8+sx%8
     if off>=len(compressed):raise ValueError('compressed tile %x > %x'%(off,len(compressed)))
     c=compressed[off]
    if c and(x+ix,y+iy)not in pts:pts[x+ix,y+iy]=c
 if not pts:return dict(w=1,h=1,px=0,py=0,pixels=b'\0')
 x0=min(x for x,y in pts);y0=min(y for x,y in pts);w=max(x for x,y in pts)-x0+1;h=max(y for x,y in pts)-y0+1
 buf=bytearray(w*h)
 for(x,y),c in pts.items():buf[(y-y0)*w+x-x0]=c
 return dict(w=w,h=h,px=-x0,py=-y0,pixels=bytes(buf))
for id in ids:
 table=u32(names['LoadCues_Data']+id*2);label=rev.get(table,'');handler=u32(names['Obj_Enemy']+(id-0xe)*2);normal=id<=0x4c or id in range(0x8a,0x9e,2)
 if not(0<table<len(r)-200):skipped.append([id,'no animation table']);continue
 # Tables can change label prefix (notably Shiva) or begin with a negative
 # displacement. Count consecutive source relative-word entries, rather than
 # inferring the size from names or the first destination address.
 match=re.search(r'^'+re.escape(label)+r':',asm,re.M)
 modes=[]
 if match:
  for line in asm[match.start():].splitlines():
   code=line.split(';',1)[0].strip()
   if not code:continue
   entry=re.fullmatch(r'(?:[A-Za-z_][A-Za-z_0-9]*:\s*)?dc\.w\s+[A-Za-z_][A-Za-z_0-9]*(?:\+\$[0-9A-F]+)?-[A-Za-z_][A-Za-z_0-9]*',code,re.I)
   if not entry:break
   modes.append(len(modes)*2)
 if not modes and match:
  # Some tiny weapon tables are emitted as numeric words by IDA. Their
  # first positive displacement is exactly the table byte length.
  first=s16(table)
  if 0<first<=256 and not(first&1) and re.match(r'[^:]+:dc\.w\s+(?:\$[0-9A-F]+|[0-9]+)\b',asm[match.start():],re.I):
   modes=list(range(0,first,2))
 if not modes:
  skipped.append([id,'animation table has no verified source boundary',label]);continue
 actor=dict(id=id,name=label.replace('AniScript_','').removesuffix('_0'),entry=handler,table=table,animations=[],normal=normal)
 for mode in modes:
  sc=table+mode+s16(table+mode)
  if not(0<sc<len(r)-16)or not(0<u16(sc)<256):invalid.append([id,mode,'bad script']);continue
  n=u16(sc);rawkind=(u16(sc+10)>>8)==0x95;stride=14 if rawkind else 8;rows=[];rec=sc+2
  try:
   for j in range(n):
    mapping=u32(rec+2)&~1;rawart=0;mutable_ram=0;record_raw=rawkind
    # Yamato animation 18 switches from DMA to resident Nemesis art at
    # the final frame. Its last row has no DMA words (word_12C140 follows).
    if id in (0x40,0x92) and mode==0x18 and j==n-1:record_raw=False
    if record_raw:
     regs=[u16(rec+8+i*2)for i in range(3)];assert [v>>8 for v in regs]==[0x95,0x96,0x97],(hex(id),hex(mode),j,regs)
     rawart=((regs[0]&255)|((regs[1]&255)<<8)|((regs[2]&127)<<16))*2
     if rawart==0xffa900 and id in (0x40,0x92):
      mutable_ram=rawart;rawart=names['ArtUnc_YamatoA']
    comp=art(artlabels[id])if not record_raw and id in artlabels else static
    key=(mapping,rawart,artlabels.get(id,'static')if not record_raw else'raw')
    if key not in poses:
     pose=render(mapping,rawart,comp);assert pose['w']<=512 and pose['h']<=512
     pose.update(key=len(poses),mapping=mapping,raw_art=rawart,art=key[2]);poses[key]=pose
    f=poses[key];rows.append(dict(ticks=u16(rec),pose=f['key'],hurt=r[mapping+2],flip=u32(rec+2)&1,mutable_ram=mutable_ram,collision=r[rec+6],damage=r[rec+7],record=rec,mapping=mapping,raw_art=rawart))
    rec+=14 if record_raw else 8
  except Exception as e:
   invalid.append([id,mode,str(e)]);continue
  actor['animations'].append(dict(mode=mode,script=sc,raw=rawkind,frames=rows))
 actors.append(actor);print(hex(id),actor['name'],len(actor['animations']),'animations',flush=True)
# Tight global atlas packing, with 4-bit indices. Pages are compressed independently.
entries=sorted(poses.values(),key=lambda f:(f['h'],f['w']),reverse=True);pages=[];atlas=bytearray(512*512);x=y=row=0;page=0
for f in entries:
 if x+f['w']>512:x=0;y+=row+1;row=0
 if y+f['h']>512:pages.append(bytes(atlas));atlas=bytearray(512*512);x=y=row=0;page+=1
 f.update(page=page,u=x,v=y)
 for yy in range(f['h']):atlas[(y+yy)*512+x:(y+yy)*512+x+f['w']]=f['pixels'][yy*f['w']:(yy+1)*f['w']]
 x+=f['w']+1;row=max(row,f['h'])
pages.append(bytes(atlas))
def packbits(raw):
 out=bytearray();i=0
 while i<len(raw):
  end=i+1
  while end<len(raw)and raw[end]==raw[i]and end-i<128:end+=1
  if end-i>=3:out.extend([128+end-i-1,raw[i]]);i=end;continue
  start=i;i=end
  while i<len(raw)and i-start<128:
   run=1
   while i+run<len(raw)and raw[i+run]==raw[i]and run<3:run+=1
   if run>=3:break
   i+=min(run,128-(i-start))
  out.append(i-start-1);out.extend(raw[start:i])
 return out
chunks=[];page_records=[];offset=0
for page in pages:
 packed=bytes(page[i]|page[i+1]<<4 for i in range(0,len(page),2));sw=bytearray()
 for by in range(0,512,8):
  for bx in range(0,256,16):
   for dy in range(8):sw+=packed[(by+dy)*256+bx:(by+dy)*256+bx+16]
 chunk=packbits(sw);chunks.append(chunk);page_records.append(dict(offset=offset,bytes=len(chunk),sha256=hashlib.sha256(sw).hexdigest()));offset+=len(chunk)
(p/'assets/bk3-graphics.bin').write_bytes(b''.join(chunks))
manifest=dict(source_rom_sha256=hashlib.sha256(r).hexdigest(),source_asm_sha256=hashlib.sha256((p/'original/vendor/BK3.asm').read_bytes()).hexdigest(),actors=actors,poses=[dict({k:v for k,v in f.items()if k!='pixels'},pixel_sha256=hashlib.sha256(f['pixels']).hexdigest())for f in sorted(poses.values(),key=lambda f:f['key'])],pages=page_records,default_palette_words=pal,composite_art=composites,skipped=skipped,invalid=invalid)
(p/'assets/bk3-full-source.json').write_text(json.dumps(manifest,indent=2))
print('TOTAL',len(actors),'objects',len(poses),'poses',len(pages),'pages',offset,'compressed bytes','invalid',len(invalid));print('FIRST INVALID',invalid[:30])
# Emit compact native lookup tables. Pages stay in system RAM (T4), no VRAM
# allocation. Source mapping flip and hurt byte are separate from pose pixels.
def fnv(raw):
 h=2166136261
 for v in raw:h=((h^v)*16777619)&0xffffffff
 return h
pose_list=sorted(poses.values(),key=lambda f:f['key'])
records=[];actor_rows=[];actor_palettes=[];collision_rows=[];collision_meta=[]
dispatch_count=(names['Data_Atk_Collision']-names['Data_Hit_Collision'])//4
collision_targets=sorted(set(u32(names['Data_Hit_Collision']+i*4)for i in range(dispatch_count*2)))
for actor in actors:
 palette=list(pal)
 oid=actor['id']
 if oid in (0x40,0x92):palette=[u16(names['Pal_Yamato']+i*2)for i in range(16)]
 elif oid in (0x3a,0x3c,0x8e,0x90):palette=[u16(names['Pal_MonaLisa']+i*2)for i in range(16)]
 elif oid in (0x32,0x38,0x44,0x94,0x96,0x98,0x9a,0x9c):
  src=names['Pal_Jet'if oid==0x44 else'Pal_RobotX']
  for off in range(0,256,2):
   word=u16(src+off);index=((word>>12)&15)|(word&16)|((word&256)>>3)
   palette[index&15]=word&0xeee
   if word&1:break
 actor_palettes.append(palette)
 boxmeta=[]
 for key,base,field in [('hurt_boxes','Data_Hit_Collision','hurt'),('attack_boxes','Data_Atk_Collision','collision')]:
  ptr=u32(names[base]+oid*2)
  maxid=max(f[field]for anim in actor['animations']for f in anim['frames'])
  nextptr=next((v for v in collision_targets if ptr<v<0x50000),None)
  count=max(maxid+1,(nextptr-ptr)//8) if nextptr and 0x4b000<=ptr<0x50000 else maxid+1 if 0x4b000<=ptr<0x50000 else 0
  # Source dispatch is pointer + index*8; adjacent/aliased tables are not
  # bounded by the next pointer. Preserve exact bytes for shared animations.
  assert not count or ptr+count*8<=0x50000
  assert not count or count>maxid,(hex(oid),key,count,maxid)
  assert not actor['normal'] or count,(hex(oid),key,hex(ptr))
  actor[key]=[list(struct.unpack_from('8b',r,ptr+k*8))for k in range(count)]
  actor[key+'_address']=ptr
  boxmeta.extend([len(collision_rows),count]);collision_rows.extend(actor[key])
 collision_meta.append(boxmeta)
 rows={f['record']:f for anim in actor['animations']for f in anim['frames']}
 start=len(records);records.extend(rows[k]for k in sorted(rows))
 actor_rows.append((oid,start,len(rows),actor['animations'][0]['frames'][0]['record']))
out=['/* Generated by prepare_bk3_full.py; original BK3 records. */']
out.append('static const Bk3GfxPose bk3gfx_poses[]={'+','.join('{'+','.join(str(f[k])for k in ['page','u','v','w','h','px','py'])+'}'for f in pose_list)+'};')
out.append('static const Bk3GfxRecord bk3gfx_records[]={'+','.join('{%d,%d,%d,%d,%d,%d}'%(f['record'],f['pose'],f['flip'],f['hurt'],f['collision'],f['damage'])for f in records)+'};')
out.append('static const Bk3GfxActor bk3gfx_actors[]={'+','.join('{%d,%d,%d,%d}'%row for row in actor_rows)+'};')
out.append('static const signed char bk3gfx_boxes[][8]={'+','.join('{'+','.join(str(v)for v in row)+'}'for row in collision_rows)+'};')
out.append('static const unsigned short bk3gfx_box_meta[][4]={'+','.join('{%d,%d,%d,%d}'%tuple(row)for row in collision_meta)+'};')
out.append('static const unsigned short bk3gfx_palettes[][16]={'+','.join('{'+','.join(str(x)for x in pal)+'}'for pal in actor_palettes)+'};')
page_meta=[]
for k,page in enumerate(pages):
 packed=bytes(page[i]|page[i+1]<<4 for i in range(0,len(page),2));sw=bytearray()
 for by in range(0,512,8):
  for bx in range(0,256,16):
   for dy in range(8):sw+=packed[(by+dy)*256+bx:(by+dy)*256+bx+16]
 page_meta.append((page_records[k]['offset'],page_records[k]['bytes'],fnv(sw)))
out.append('static const unsigned bk3gfx_pages[][3]={'+','.join('{%d,%d,%du}'%row for row in page_meta)+'};')
(p/'src/bk3gfx_data.h').write_text('\n'.join(out)+'\n')
(p/'assets/bk3-full-source.json').write_text(json.dumps(manifest,indent=2))
# Contact sheets show the first standing pose of every original actor.
rgba=bytearray(bytes([24,24,32,255])*1024*(((len(actors)+7)//8)*144));H=len(rgba)//4096
palrgb=[tuple(((v>>s)&14)*255//14 for s in(0,4,8))+(255,)for v in pal]
ps={f['key']:f for f in poses.values()}
for k,a in enumerate(actors):
 if not a['animations']:continue
 palrgb=[tuple(((v>>s)&14)*255//14 for s in(0,4,8))+(255,)for v in actor_palettes[k]]
 f=ps[a['animations'][0]['frames'][0]['pose']];ox=k%8*128+64-f['px'];oy=k//8*144+130-f['py']
 for yy in range(f['h']):
  for xx in range(f['w']):
   c=f['pixels'][yy*f['w']+xx];sx=ox+xx;sy=oy+yy
   if c and 0<=sx<1024 and 0<=sy<H:rgba[(sy*1024+sx)*4:(sy*1024+sx)*4+4]=bytes(palrgb[c])
png(p/'assets/bk3-full-contact.png',1024,H,rgba)
