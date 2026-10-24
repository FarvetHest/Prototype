from pathlib import Path
import re,json,hashlib,struct
from prepare_sprites import png
P=Path(__file__).resolve().parents[1]
ASM=P/'original/vendor/BK3.asm'
assert hashlib.sha256(ASM.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
lines=ASM.read_text(errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(lines)if(m:=re.match(r'^(\w+):',l))}
def dat(name):
 out=bytearray()
 for i,line in enumerate(lines[labels[name]:]):
  if i and re.match(r'^\w+:',line):break
  m=re.search(r'dc\.([bwl])\s+([^;]+)',line)
  if m:
   n={'b':1,'w':2,'l':4}[m[1]]
   for s in m[2].split(','):
    s=s.strip();v=int(s[1:],16)if s.startswith('$')else int(s);out.extend(v.to_bytes(n,'big'))
 return out
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
def main():
 art=nemesis(dat('ArtNem_HUD'));assert len(art)==67*64
 words=struct.unpack('>104H',dat('Ani_SpecialBar'));pal=[(0,0,0,0)]*16
 raw=dat('word_88C6')
 for c, in struct.iter_unpack('>H',raw):
  i=(c>>12)&15;pal[i]=((c&14)*255//14,((c>>4)&14)*255//14,((c>>8)&14)*255//14,255)
 tex=(P/'assets/hud.rgba').read_bytes();atlas=bytearray(len(tex));off=0
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):atlas[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=tex[off:off+16];off+=16
 manifest=json.loads((P/'assets/hud-manifest.json').read_text());manifest['frames']=[f for f in manifest['frames']if f['file']!='bk3_special']
 previews=bytearray(13*18*32*4)
 for frame in range(13):
  ox=1+frame*18;oy=84;rgba=bytearray(16*32*4)
  for j,a in enumerate(words[frame*8:frame*8+8]):
   tile=(a&2047)-0x6b5;assert 0<=tile<67
   for y in range(8):
    for x in range(8):
     sx=7-x if a&2048 else x;sy=7-y if a&4096 else y;c=art[tile*64+sy*8+sx];pixel=bytes(pal[c]);px=(j%2)*8+x;py=(j//2)*8+y
     atlas[((oy+py)*256+ox+px)*4:((oy+py)*256+ox+px)*4+4]=pixel
     previews[(py*234+frame*18+px)*4:(py*234+frame*18+px)*4+4]=pixel
  manifest['frames'].append(dict(file='bk3_special',id=frame,u=ox,v=oy,w=16,h=32))
 sw=bytearray()
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):sw+=atlas[(by+dy)*1024+bx:(by+dy)*1024+bx+16]
 (P/'assets/hud.rgba').write_bytes(sw);png(P/'assets/hud-atlas.png',256,256,atlas);png(P/'assets/bk3-special-states.png',234,32,previews)
 manifest['texture_sha256']=hashlib.sha256(sw).hexdigest();manifest['bk3_special']=dict(art='ArtNem_HUD',vram_base='D6A0',scripts='Ani_SpecialBar',palette='word_88C6',source_sha256=hashlib.sha256(ASM.read_bytes()).hexdigest(),states=13,size=[16,32],charge='Combat.raw_charge / 16; no percentage stretch; original 2x4 tile states')
 (P/'assets/hud-manifest.json').write_text(json.dumps(manifest,indent=2))
 header=P/'src/hud_data.h';s=header.read_text();s=re.sub(r'\{9,\d+,\d+,\d+,16,32\},\n','',s)
 s=s.replace(',HUD_BK3_SPECIAL=9','')
 s=s.replace('HUD_ITEM=7,HUD_FUENTE=8','HUD_ITEM=7,HUD_FUENTE=8,HUD_BK3_SPECIAL=9')
 if 'HUD_BK3_SPECIAL' not in s:s=s.replace('HUD_FUENTE=8','HUD_FUENTE=8,HUD_BK3_SPECIAL=9')
 entries=''.join('{9,'+','.join(str(f[k])for k in ['id','u','v','w','h'])+'},\n'for f in manifest['frames']if f['file']=='bk3_special')
 s=s.replace('};\n#define HUD_FRAME_COUNT',entries+'};\n#define HUD_FRAME_COUNT');header.write_text(s)
 print(json.dumps(manifest['bk3_special'],indent=2))
if __name__=='__main__':main()
