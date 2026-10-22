"""Original SoRR HUD pixels, composed into a single lossless RGBA8888 atlas."""
from pathlib import Path
import argparse,hashlib,json,struct
from prepare_sprites import decode,png
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);args=ap.parse_args()
    choose={'barra':[24],'barra_amarilla':[24],'barra_azul':[24],'sorr':[176,250],
            'galsia':[300],'donovan':[300],'general':[10],'item':[4,18],
            'fuente':list(range(48,58))+list(range(97,123))+[33,58,63]+list(range(248,258))}
    atlas=bytearray(256*256*4);entries=[];sources=[];x=y=1;row=0
    for name,ids in choose.items():
        path=args.data/(name+'.fpg');pal,maps=decode(path)
        sources.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ids':ids})
        for code in ids:
            frame=maps[code];w,h=frame['w'],frame['h']
            if x+w+1>256:x=1;y+=row+2;row=0
            assert y+h+1<256
            for sy in range(h):
                for sx in range(w):
                    index=frame['pixels'][sy*w+sx];off=((y+sy)*256+x+sx)*4
                    atlas[off:off+4]=bytes(pal[index])
            entries.append({'file':name,'id':code,'u':x,'v':y,'w':w,'h':h})
            x+=w+2;row=max(row,h)
    swizzled=bytearray()
    for by in range(0,256,8):
        for bx in range(0,1024,16):
            for dy in range(8):swizzled+=atlas[(by+dy)*1024+bx:(by+dy)*1024+bx+16]
    restored=bytearray(len(atlas));offset=0
    for by in range(0,256,8):
        for bx in range(0,1024,16):
            for dy in range(8):restored[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=swizzled[offset:offset+16];offset+=16
    assert restored==atlas
    dest=ROOT/'assets';(dest/'hud.rgba').write_bytes(swizzled);png(dest/'hud-atlas.png',256,256,atlas)
    lines=['/* Generated original SoRR UI art. */','#ifndef HUD_DATA_H','#define HUD_DATA_H',
           'typedef struct { short set,id,u,v,w,h; } HudFrame;',
           'extern const unsigned char hud_texture[];',
           'enum { '+','.join('HUD_'+n.upper()+'='+str(i) for i,n in enumerate(choose))+' };',
           'static const HudFrame hud_frames[] = {']
    for e in entries:lines.append('{'+','.join(map(str,[list(choose).index(e['file']),e['id'],e['u'],e['v'],e['w'],e['h']]))+'},')
    lines+=['};','#define HUD_FRAME_COUNT (sizeof(hud_frames)/sizeof(hud_frames[0]))','#endif']
    (ROOT/'src/hud_data.h').write_text('\n'.join(lines)+'\n')
    (dest/'hud-manifest.json').write_text(json.dumps({'sources':sources,'frames':entries,'texture_bytes':len(swizzled),'texture_sha256':hashlib.sha256(swizzled).hexdigest(),'format':'256x256 GU_PSM_8888 swizzled; original 6-bit palette expanded to 8-bit; index 0 transparent','swizzle_roundtrip_verified':True},indent=2))
    print('Prepared',len(entries),'original HUD images in',len(swizzled),'bytes')
if __name__=='__main__':main()

