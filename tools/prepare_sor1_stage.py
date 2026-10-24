from pathlib import Path
import re,struct,hashlib,json,sys
from prepare_sprites import png
P=Path(__file__).resolve().parents[1]
ASM=P/'original/vendor/SOR1.asm'
assert hashlib.sha256(ASM.read_bytes()).hexdigest()=='f14690a8fa50b081be5c04533e482b68ff2d1d9e7760d45c5105a86fa26a8300'
ls=ASM.read_text(errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}
def num(s):
 s=s.strip()
 if '-'in s:
  a,b=s.split('-',1);return num(a)-num(b)
 if '+'in s:return sum(map(num,s.split('+')))
 if s in labels:return int(s.split('_')[-1],16)
 return int(s[1:],16)if s.startswith('$')else int(s)
def dat(name):
 o=bytearray()
 for i,l in enumerate(ls[labels[name]:]):
  if i and re.match(r'^\w+:',l):break
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if m:
   n={'b':1,'w':2,'l':4}[m[1]]
   for v in m[2].split(','):o.extend((num(v)&((1<<(n*8))-1)).to_bytes(n,'big'))
 return o
addrnames={num(k):k for k in labels if re.match(r'^(byte|word|dword|off)_[0-9A-F]+$',k)}
def at(a):return dat(addrnames[a])
def kos(raw):
 pos=2;desc=int.from_bytes(raw[:2],'little');left=16;out=bytearray()
 def bit():
  nonlocal desc,left,pos
  b=desc&1;desc>>=1;left-=1
  if not left:desc=int.from_bytes(raw[pos:pos+2],'little');pos+=2;left=16
  return b
 def byte():
  nonlocal pos
  r=raw[pos];pos+=1;return r
 while True:
  if bit():out.append(byte());continue
  if not bit():
   n=(bit()<<1)|bit();n+=2;off=byte()-256
  else:
   lo=byte();hi=byte();off=((hi&248)<<5)|lo;off-=8192;n=hi&7
   if n:n+=2
   else:
    n=byte()
    if n==0:return out
    if n==1:continue
    n+=1
  for _ in range(n):out.append(out[len(out)+off])
  assert len(out)<2000000

def eni(raw):
 n,flags=raw[:2];inc=int.from_bytes(raw[2:4],'big');fixed=int.from_bytes(raw[4:6],'big');cursor=48;out=[]
 def bits(n):
  nonlocal cursor
  v=0
  for _ in range(n):v=v*2+((raw[cursor//8]>>(7-cursor%8))&1);cursor+=1
  return v
 def value():
  attr=0
  for j in range(5):
   if flags&(16>>j):attr|=bits(1)<<(15-j)
  return attr+bits(n)
 while True:
  if not bits(1):
   k=bits(1);count=bits(4)+1
   for _ in range(count):
    out.append(fixed if k else inc)
    if not k:inc=(inc+1)&65535
  else:
   k=bits(2);count=bits(4)+1
   if k==3:
    if count==16:break
    for _ in range(count):out.append(value())
   else:
    v=value()
    for _ in range(count):out.append(v&65535);v+=0 if k==0 else 1 if k==1 else -1
  assert len(out)<50000
 return out

def expand(name,stride):
 d=dat(name);bank=kos(at(int.from_bytes(d[:4],'big')));pos=6;dest=0;out=bytearray(stride*128);groups=[]
 while True:
  rows=int.from_bytes(d[pos:pos+2],'big');pos+=2
  if rows==65535:break
  ratio=int.from_bytes(d[pos:pos+4],'big');pos+=4;mode=int.from_bytes(d[pos:pos+2],'big');pos+=2;x=0
  if mode==2:raise ValueError('vertical map')
  while True:
   chunk=int.from_bytes(d[pos:pos+2],'big');pos+=2
   if chunk==65535:break
   for y in range(rows+1):
    for k in range(16):out[dest+y*stride+x+k]=bank[chunk*256+y*16+k]
   x+=16
  advance=int.from_bytes(d[pos:pos+2],'big');pos+=2;groups.append(dict(rows=rows+1,chunks=x//16,ratio=ratio,mode=mode,base=dest,advance=advance));dest+=advance
 return out,groups

def palette(raw):
 pal=[(0,0,0,255)]*64
 for i in range(0,len(raw),2):
  c=int.from_bytes(raw[i:i+2],'big');index=(c&16)|((c>>12)&15)|((c&256)>>3);v=c&0xeee;pal[index]=((v&14)*255//14,((v>>4)&14)*255//14,((v>>8)&14)*255//14,255)
  if c&1:break
 return pal


def main():
 d=dat('dword_5F5C8');ptrs=struct.unpack_from('>8I',d);vram=bytearray(65536)
 for i in [0,2]:
  cmd,addr=ptrs[i:i+2];art=kos(at(addr));dest=((cmd>>16)&0x3fff)|((cmd&3)<<14);vram[dest:dest+len(art)]=art
 assert not any(vram[:32]),'runtime skips transparent tile 0'
 defs=[eni(at(ptrs[4])),eni(at(ptrs[5]))];pal=palette(at(ptrs[7]));maps=[];groups=[]
 for name in ['off_5F7A8','off_5F9DA']:
  m,g=expand(name,336);maps.append(m[:336*15]);groups.append(g)
 used=max(a&2047 for ds in defs for a in ds)+1;assert used*4<=4096
 atlas=bytearray(512*512)
 for tile in range(used):
  for bank in range(4):
   i=tile*4+bank;ox=(i%64)*8;oy=(i//64)*8
   for y in range(8):
    for x in range(8):
     c=(vram[tile*32+y*4+x//2]>>(4 if x%2==0 else 0))&15
     atlas[(oy+y)*512+ox+x]=bank*16+c
 colors=[(r|(g<<8)|(b<<16)|(255<<24)) if i%16 else 0 for i,(r,g,b,_) in enumerate(pal)]
 text='#ifndef LITE_STAGE_DATA_H\n#define LITE_STAGE_DATA_H\n#define STAGE_BYTES 262144\n#define STAGE_WIDTH 5376\n#define STAGE_MAP_STRIDE 336\n#define STAGE_MAP_ROWS 15\n'
 for name,values,ctype in [('stage_palette',colors,'unsigned int'),('stage_defs_a',defs[0],'unsigned short'),('stage_defs_b',defs[1],'unsigned short'),('stage_map_a',maps[0],'unsigned char'),('stage_map_b',maps[1],'unsigned char')]:
  text+='static const '+ctype+' __attribute__((aligned(16))) '+name+'[]={\n'
  for i in range(0,len(values),16):text+=','.join(hex(v)for v in values[i:i+16])+',\n'
  text+='};\n'
 text+='#endif\n';(P/'src/stage_data.h').write_text(text)
 (P/'assets/stage.t8').write_bytes(atlas)
 # Export independent-looking, unscaled 320x224 source-map reference crops for visual review.
 for camera in [0,2048,4896]:
  w,h=320,224;rgba=bytearray(bytes((0,0,0,255))*(w*h))
  for priority in [0,1]:
   for layer in [1,0]:
    for y in range(h):
     for x in range(w):
      wx=camera+x;block=maps[layer][(y//16)*336+wx//16];idx=block*4+((y%16)//8)*2+(wx%16)//8
      if idx>=len(defs[layer]):continue
      a=defs[layer][idx]
      if (a>>15)!=priority:continue
      sx=wx%8;sy=y%8
      if a&2048:sx=7-sx
      if a&4096:sy=7-sy
      off=(a&2047)*32+sy*4+sx//2;c=(vram[off]>>(4 if sx%2==0 else 0))&15
      if c:rgba[(y*w+x)*4:(y*w+x)*4+4]=bytes(pal[((a>>13)&3)*16+c])
  png(P/'assets'/('route1-round1-'+str(camera)+'.png'),w,h,rgba)
 report=dict(source='SOR1 REV00 disassembly',source_sha256=hashlib.sha256(ASM.read_bytes()).hexdigest(),repository='https://github.com/gsaurus/sor-disassemblies',commit='4dd719f3ed5c24c86deee616b56cea885e3113d7',descriptor='dword_5F5C8',layouts=['off_5F7A8','off_5F9DA'],dimensions=[5376,240],display_height=224,tile_count=used,atlas_bytes=len(atlas),atlas_sha256=hashlib.sha256(atlas).hexdigest(),map_bytes=sum(map(len,maps)),groups=groups,rounds_in_source=8,rounds_connected=1,enemy_encounters='Lite authored adapters, not original SoR1 cue interpreter',music='Unchanged SoRR Go Straight track; SoR1 music pending')
 (P/'assets/route1-manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
