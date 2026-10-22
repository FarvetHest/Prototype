"""Prepare all columns of the original stage1g in independent swizzled RAM pages."""
from pathlib import Path
import argparse,hashlib,json,struct
from prepare_sprites import png
ap=argparse.ArgumentParser();ap.add_argument('--fpg',type=Path,required=True);a=ap.parse_args();p=Path(__file__).resolve().parents[1]
data=a.fpg.read_bytes();assert data[:8]==b'f16\x1a\r\n\0\0';off=8;chosen=None
while off<len(data):
 code,size,name,fn,w,h,cp=struct.unpack_from('<2i32s12s3i',data,off);start=off+64+cp*4;end=start+w*h*2
 assert end<=len(data)
 if code==1:chosen=(w,h,data[start:end])
 off=end
assert chosen and off==len(data);w,h,source=chosen;assert w==2852 and h==240
pages=(w+511)//512;output=bytearray();preview=bytearray(w*h*4)
for page in range(pages):
 tex=bytearray(512*256*2)
 for y in range(h):
  for x in range(min(512,w-page*512)):
   v=struct.unpack_from('<H',source,(y*w+page*512+x)*2)[0];psp=((v&31)<<11)|(v&0x7e0)|((v>>11)&31)
   struct.pack_into('<H',tex,(y*512+x)*2,psp);k=(y*w+page*512+x)*4;preview[k:k+4]=bytes((((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31,255))
 sw=bytearray()
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):sw+=tex[(by+dy)*1024+bx:(by+dy)*1024+bx+16]
 restored=bytearray(len(tex));pos=0
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):restored[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=sw[pos:pos+16];pos+=16
 assert restored==tex
 output+=sw
(p/'assets/stage.rgb565').write_bytes(output);png(p/'assets/stage-full-preview.png',w,h,preview)
m=json.loads((p/'assets/stage-manifest.json').read_text());m.update(stage_sha256=hashlib.sha256(data).hexdigest(),source_dimensions=[w,h],texture_dimensions=[512,256],pages=pages,visible_crop=[0,0,w,h],texture_bytes=len(output),texture_sha256=hashlib.sha256(output).hexdigest(),first_page_sha256=hashlib.sha256(output[:262144]).hexdigest(),page_sha256=[hashlib.sha256(output[i*262144:(i+1)*262144]).hexdigest()for i in range(pages)],storage='six static RAM pages; no VRAM background copy')
(p/'assets/stage-manifest.json').write_text(json.dumps(m,indent=2));(p/'src/stage_data.h').write_text('#define STAGE_PAGES %d\n#define STAGE_BYTES %d\n'%(pages,len(output)))
print('Prepared',w,'x',h,'in',pages,'pages,',len(output),'RAM bytes')
