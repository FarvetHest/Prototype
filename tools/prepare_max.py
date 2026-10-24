"""Pack original SoRR Max sprites and authored BK3-state aliases without editing pixels."""
from pathlib import Path
import json,hashlib,struct
from prepare_sprites import decode,png
P=Path(__file__).resolve().parents[1]
# BK3 state pose -> existing Max FPG pose. This is a Lite mechanics adapter.
ALIASES={1:1,2:2,3:3,4:2,32:1,33:3,5:4,6:5,7:6,8:7,9:8,10:9,168:168,169:169,170:170,171:171,172:172,173:173,60:11,12:12,13:13,80:10,81:24,82:25,83:24,84:25,85:26,86:27,61:35,62:36,63:37,64:38,65:36,66:37,67:35,18:14,19:15,20:16,21:20,22:15,23:16,24:24,25:25,26:26,27:27,28:28,29:24,30:25,31:26,34:35,35:36,36:37,37:38,38:36,39:37,40:38,41:36,42:37,43:35,44:11,45:12,46:13,53:47,68:68,79:68,69:69,70:71,71:68,72:72,73:72,100:12,153:153,154:154,155:155,156:156,157:157,158:158,159:159,900:11,901:12,902:18,903:13,904:11,148:148,47:47,48:48,49:49,50:50,51:51,99:99,98:98,101:11,102:99,132:98,133:99,134:11,14:55,15:56,16:57,17:58,910:74,920:77,921:77,922:48,923:148}

def main():
 source=P/'original/max.fpg';assert hashlib.sha256(source.read_bytes()).hexdigest()=='399ea5927d7385c28a220fbd88cd988ce87df2c51d6aa90c575097733745135a';pal,frames=decode(source);required=sorted(set(ALIASES.values()));assert all(i in frames for i in required)
 atlas=bytearray(512*1536);x=y=1;row=0;entries=[]
 for i in required:
  f=frames[i];w,h=f['w'],f['h']
  if x+w+1>512:x=1;y+=row+2;row=0
  if y//512!=(y+h)//512:x=1;y=(y//512+1)*512+1;row=0
  assert y+h<1536
  for sy in range(h):atlas[(y+sy)*512+x:(y+sy)*512+x+w]=f['pixels'][sy*w:(sy+1)*w]
  entries.append(dict(id=i,u=x,v=y,w=w,h=h,px=f['pivot'][0],py=f['pivot'][1],pixel_sha256=hashlib.sha256(f['pixels']).hexdigest()));x+=w+2;row=max(row,h)
 pages=(y+row+511)//512;atlas=atlas[:pages*262144];sw=bytearray()
 for by in range(0,pages*512,8):
  for bx in range(0,512,16):
   for dy in range(8):sw+=atlas[(by+dy)*512+bx:(by+dy)*512+bx+16]
 dest=P/'assets';(dest/'max.t8').write_bytes(sw)
 header=['/* Original SoRR Max pixels/pivots; BK3 move mapping is an adapter. */','#ifndef MAX_DATA_H','#define MAX_DATA_H',f'#define MAX_TEXTURE_BYTES {len(sw)}','extern const unsigned char max_atlas[];','static const unsigned __attribute__((aligned(16))) max_palette[256]={'+','.join(hex(r|(g<<8)|(b<<16)|(a<<24))+'u'for r,g,b,a in pal)+'};','static const SpriteFrame max_frames[]={']
 for e in entries:header.append('{6,'+','.join(str(e[k])for k in ['id','u','v','w','h','px','py'])+'},')
 header+=['};','static const unsigned short max_aliases[][2]={']+['{'+str(k)+','+str(v)+'},'for k,v in sorted(ALIASES.items())]+['};','#endif'];(P/'src/max_data.h').write_text('\n'.join(header)+'\n')
 (P/'src/max_texture.S').write_text('.section .rodata\n.balign 16\n.global max_atlas\n.type max_atlas, @object\nmax_atlas:\n.incbin "assets/max.t8"\n.size max_atlas, . - max_atlas\n')
 width=1200;height=((len(required)+11)//12)*130;rgba=bytearray(bytes((32,32,48,255))*(width*height))
 for j,i in enumerate(required):
  f=frames[i];px,py=f['pivot'];ox=j%12*100+50-px;oy=j//12*130+112-py
  for sy in range(f['h']):
   for sx in range(f['w']):
    c=f['pixels'][sy*f['w']+sx]
    if c and 0<=ox+sx<width and 0<=oy+sy<height:off=((oy+sy)*width+ox+sx)*4;rgba[off:off+4]=bytes(pal[c])
 png(dest/'max-contact.png',width,height,rgba)
 # Original Max HUD portrait, never synthesize a face from another character.
 portrait=frames[300];print('portrait',portrait['w'],portrait['h']);assert portrait['w']<=24 and portrait['h']<=24
 raw=(dest/'hud.rgba').read_bytes();linear=bytearray(len(raw));o=0
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):linear[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=raw[o:o+16];o+=16
 pw,ph=portrait['w'],portrait['h'];prgba=b''.join(bytes(pal[c])for c in portrait['pixels'])
 for sy in range(ph):linear[((122+sy)*256+1)*4:((122+sy)*256+1+pw)*4]=prgba[sy*pw*4:(sy+1)*pw*4]
 png(dest/'max-portrait.png',pw,ph,prgba);hud=bytearray()
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):hud+=linear[(by+dy)*1024+bx:(by+dy)*1024+bx+16]
 (dest/'hud.rgba').write_bytes(hud);m=json.loads((dest/'hud-manifest.json').read_text());m['frames']=[f for f in m['frames']if f['file']!='max_portrait'];m['frames'].append(dict(file='max_portrait',id=0,u=1,v=122,w=pw,h=ph));m['texture_sha256']=hashlib.sha256(hud).hexdigest();(dest/'hud-manifest.json').write_text(json.dumps(m,indent=2))
 hf=P/'src/hud_data.h';s=hf.read_text().replace(',HUD_MAX=10','').replace('HUD_BK3_SPECIAL=9','HUD_BK3_SPECIAL=9,HUD_MAX=10');s='\n'.join(l for l in s.splitlines()if not l.startswith('{10,'))+'\n';s=s.replace('};\n#define HUD_FRAME_COUNT',f'{{10,0,1,122,{pw},{ph}}},\n}};\n#define HUD_FRAME_COUNT');hf.write_text(s)
 manifest=dict(source_file='original/max.fpg',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),palette=pal,frames=entries,aliases=ALIASES,frame_count=len(entries),atlas_pages=pages,atlas_bytes=len(sw),atlas_sha256=hashlib.sha256(sw).hexdigest(),source_pixel_and_pivots_unchanged=True,art='Existing SoRR Max pixel sprites; original authorship retained',limits='Single-player heavyweight adapter on shared BK3/Lite logic; not a full port of original SoR2 Max code. No HD resampling or invented body/limb parts.')
 (dest/'max-manifest.json').write_text(json.dumps(manifest,indent=2));print('Max:',len(entries),'original poses;',pages,'RAM pages;',len(sw),'bytes')
if __name__=='__main__':main()
