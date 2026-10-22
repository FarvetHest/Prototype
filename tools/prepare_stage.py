"""Prepare a lossless RGB565 crop of original stage1g; retain original OGG."""
from pathlib import Path
import argparse,hashlib,json,struct,shutil
from prepare_sprites import png
PROJECT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fpg',type=Path,required=True);ap.add_argument('--music',type=Path,required=True);args=ap.parse_args()
    data=args.fpg.read_bytes();assert data[:8]==b'f16\x1a\r\n\0\0'
    off=8;chosen=None
    while off<len(data):
        code,size,name,fn,w,h,cp=struct.unpack_from('<2i32s12s3i',data,off)
        start=off+64+cp*4;end=start+w*h*2
        assert 0<w<16384 and 0<h<16384 and end<=len(data)
        if code==1:chosen=(w,h,data[start:end])
        off=end
    assert chosen and off==len(data)
    w,h,source=chosen;assert w>=512 and h==240
    tex=bytearray(512*256*2);preview=bytearray()
    for y in range(240):
        for x in range(512):
            rgb=struct.unpack_from('<H',source,(y*w+x)*2)[0]
            psp=((rgb&31)<<11)|(rgb&0x7e0)|((rgb>>11)&31)
            struct.pack_into('<H',tex,(y*512+x)*2,psp)
            if x<480:preview+=bytes((((rgb>>11)&31)*255//31,((rgb>>5)&63)*255//63,(rgb&31)*255//31,255))
    swizzled=bytearray()
    for by in range(0,256,8):
        for bx in range(0,1024,16):
            for dy in range(8):swizzled+=tex[(by+dy)*1024+bx:(by+dy)*1024+bx+16]
    restored=bytearray(len(tex));o=0
    for by in range(0,256,8):
        for bx in range(0,1024,16):
            for dy in range(8):restored[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=swizzled[o:o+16];o+=16
    assert restored==tex
    dest=PROJECT/'assets';dest.mkdir(exist_ok=True)
    (dest/'stage.rgb565').write_bytes(swizzled);png(dest/'stage-preview.png',480,240,preview)
    shutil.copy2(args.music,PROJECT/'music.ogg')
    ogg=args.music.read_bytes();ident=ogg.index(b'\x01vorbis');channels,rate=struct.unpack_from('<BI',ogg,ident+11)
    last=ogg.rfind(b'OggS');total=struct.unpack_from('<Q',ogg,last+6)[0]
    assert channels==2 and rate==44100
    report={'stage_file':args.fpg.name,'stage_sha256':hashlib.sha256(data).hexdigest(),'map_id':1,'source_dimensions':[w,h],'texture_dimensions':[512,256],'visible_crop':[0,0,480,240],'screen_position':[0,32],'texture_bytes':len(swizzled),'texture_sha256':hashlib.sha256(swizzled).hexdigest(),'swizzle_roundtrip_verified':True,'music_source':args.music.name,'music_title':'Go Straight (SoRR remix)','music_sha256':hashlib.sha256(ogg).hexdigest(),'music_bytes':len(ogg),'music_rate':rate,'music_channels':channels,'music_pcm_frames':total,'music_seconds':total/rate}
    (dest/'stage-manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
