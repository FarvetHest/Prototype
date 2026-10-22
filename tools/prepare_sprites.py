"""Extract a bounded native-index atlas from the user's local SoRR FPG files.
No image libraries required. Original art remains owned by its creators.
"""
import argparse, hashlib, json, struct, zlib
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
SETS={'bk3_axel':list(range(1,11))+[11,12,13,14,15,16,18,19,20,21,22,23,24,25,26,27,28]+list(range(34,44))+[47,48,49,50]+list(range(60,68))+[68,69,70,71,72,73,74,75,76,101,102,132,133,134,51,98,99,148,17,29,30,31,32,33,44,45,46,53,79,80,81,82,83,84,85,100,150,151,152,153,154,155,156,157,158,159,168,169,170,171,172,173], 'galsia':[1,2,3,4,7,8,9,12,17,18], 'donovan':[1,2,3,4,5,6,7,8,9,10,11,12,13,14,23]}

def png(path,w,h,data):
    def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
    rows=b''.join(b'\0'+data[y*w*4:(y+1)*w*4] for y in range(h))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))

def decode(path):
    data=path.read_bytes()
    if data[:8]!=b'fpg\x1a\r\n\0\0':raise ValueError('Expected original 8-bit FPG: '+str(path))
    palette=[tuple(round(c*255/63) for c in data[8+i*3:11+i*3])+(255 if i else 0,) for i in range(256)]
    assert max(data[8:776])<=63
    frames={};offset=1352
    while offset<len(data):
        code,size,name,fn,w,h,cp=struct.unpack_from('<2i32s12s3i',data,offset)
        assert 0<w<4096 and 0<h<4096 and 0<=cp<1000
        start=offset+64+cp*4;end=start+w*h
        assert end<=len(data) and size in (0,end-offset)
        pivot=struct.unpack_from('<hh',data,offset+64) if cp else (w//2,h-1)
        frames[code]={'w':w,'h':h,'pivot':pivot,'pixels':data[start:end],'title':name.split(b'\0')[0].decode('latin1')}
        offset=end
    assert offset==len(data)
    return palette,frames

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);args=ap.parse_args()
    dest=PROJECT/'assets';dest.mkdir(exist_ok=True)
    ref=json.loads((dest/'bk3-reference.json').read_text());SETS['bk3_axel']=sorted({f['fpg']for sc in ref['scripts'].values()for f in sc['frames']}|{48})
    atlas=bytearray(512*1536);entries=[];palettes=[];sources=[];pending=[]
    for family,(name,ids) in enumerate(SETS.items()):
        ids=list(dict.fromkeys(ids));path=args.data/(name+'.fpg');palette,frames=decode(path)
        native=json.loads((dest/'enemy-native.json').read_text())
        if name in native:
            data=native[name];palette=[tuple(c)for c in data['palette']]+[(0,0,0,0)]*240
            frames={int(k):dict(v,pixels=bytes.fromhex(v['pixels']))for k,v in data['frames'].items()};ids=list(frames)
        SETS[name]=ids;palettes.append(palette)
        sources.append({'file':('ArtNem_GarciaDonovan + sprite mappings')if name in native else path.name,'sha256':native[name]['source_sha256']if name in native else hashlib.sha256(path.read_bytes()).hexdigest(),'color_source':path.name,'color_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'frame_ids':ids})
        for code in ids:
            f=frames[code];points=[(i%f['w'],i//f['w'])for i,v in enumerate(f['pixels'])if v]
            assert points
            x0=min(x for x,y in points);y0=min(y for x,y in points)
            w=max(x for x,y in points)-x0+1;h=max(y for x,y in points)-y0+1
            pixels=b''.join(f['pixels'][(y0+y)*f['w']+x0:(y0+y)*f['w']+x0+w]for y in range(h))
            pending.append(dict(family=family,name=name,id=code,w=w,h=h,px=f['pivot'][0]-x0,py=f['pivot'][1]-y0,
                                source_w=f['w'],source_h=f['h'],crop_left=x0,crop_top=y0,title=f['title'],pixels=pixels))
    free=[(0,0,512,512),(0,512,512,512),(0,1024,512,512)]
    for e in sorted(pending,key=lambda f:(f['w']*f['h'],max(f['w'],f['h'])),reverse=True):
        rw,rh=e['w']+2,e['h']+2
        fits=[(min(w-rw,h-rh),max(w-rw,h-rh),x,y)for x,y,w,h in free if rw<=w and rh<=h]
        assert fits,'Atlas overflow'
        _,_,x,y=min(fits);new=[]
        for fx,fy,fw,fh in free:
            if x>=fx+fw or x+rw<=fx or y>=fy+fh or y+rh<=fy:new.append((fx,fy,fw,fh));continue
            if x>fx:new.append((fx,fy,x-fx,fh))
            if x+rw<fx+fw:new.append((x+rw,fy,fx+fw-x-rw,fh))
            if y>fy:new.append((fx,fy,fw,y-fy))
            if y+rh<fy+fh:new.append((fx,y+rh,fw,fy+fh-y-rh))
        new=list(set(new))
        free=[r for r in new if not any(r!=q and r[0]>=q[0] and r[1]>=q[1] and r[0]+r[2]<=q[0]+q[2] and r[1]+r[3]<=q[1]+q[3] for q in new)]
        e['x']=x+1;e['y']=y+1
        for sy in range(e['h']):atlas[(y+1+sy)*512+x+1:(y+1+sy)*512+x+1+e['w']]=e['pixels'][sy*e['w']:(sy+1)*e['w']]
        entries.append({k:v for k,v in e.items()if k!='pixels'})
    # PSP texture layout: 16-byte by 8-row blocks, prepared once offline.
    swizzled=bytearray()
    for by in range(0,1536,8):
        for bx in range(0,512,16):
            for dy in range(8):swizzled+=atlas[(by+dy)*512+bx:(by+dy)*512+bx+16]
    # Independent inverse-layout check before embedding the atlas.
    restored=bytearray(512*1536);offset=0
    for by in range(0,1536,8):
        for bx in range(0,512,16):
            for dy in range(8):
                restored[(by+dy)*512+bx:(by+dy)*512+bx+16]=swizzled[offset:offset+16];offset+=16
    assert restored==atlas
    dest.joinpath('sprites.t8').write_bytes(swizzled)
    header=['/* Generated from local SoRR assets. Do not hand edit. */','#ifndef SPRITE_DATA_H','#define SPRITE_DATA_H',
            'typedef struct { short family, id, u, v, w, h, px, py; } SpriteFrame;',
            'extern const unsigned char sprite_atlas[];',
            'static const unsigned __attribute__((aligned(16))) sprite_palettes[3][256] = {']
    for pal in palettes:header+=['{'+','.join(hex(r|(g<<8)|(b<<16)|(a<<24))+'u' for r,g,b,a in pal)+'},']
    header+=['};','static const SpriteFrame sprite_frames[] = {']
    for e in entries:header+=['{'+','.join(str(e[k]) for k in ('family','id','x','y','w','h','px','py'))+'},']
    header+=['};','#define SPRITE_FRAME_COUNT (sizeof(sprite_frames)/sizeof(sprite_frames[0]))','#endif']
    (PROJECT/'src/sprite_data.h').write_text('\n'.join(header)+'\n')
    # Every cell has sufficient room for its complete image and a marker at the foot.
    width,height=1200,120*sum((len(ids)+11)//12 for ids in SETS.values());sheet=bytearray(bytes((32,32,48,255))*(width*height))
    for e in entries:
        ids=SETS[e['name']];i=ids.index(e['id']);ox=(i%12)*100+50-e['px'];oy=sum((len(ids)+11)//12 for ids in list(SETS.values())[:e['family']])*120+(i//12)*120+110-e['py']
        for sy in range(e['h']):
            for sx in range(e['w']):
                idx=atlas[(e['y']+sy)*512+e['x']+sx]
                if idx:
                    off=((oy+sy)*width+ox+sx)*4;sheet[off:off+4]=bytes(palettes[e['family']][idx])
        fx=(i%12)*100+50;fy=sum((len(ids)+11)//12 for ids in list(SETS.values())[:e['family']])*120+(i//12)*120+110
        for dx in range(-3,4):sheet[(fy*width+fx+dx)*4:(fy*width+fx+dx)*4+4]=bytes((255,80,80,255))
    png(dest/'contact-sheet.png',width,height,sheet)
    (dest/'manifest.json').write_text(json.dumps({'sources':sources,'frames':entries,'atlas_bytes':len(atlas),'atlas_sha256':hashlib.sha256(swizzled).hexdigest(),'swizzle_roundtrip_verified':True,'format':'three 512x512 swizzled GU_PSM_T8 pages; global v selects page; per-family RGBA8888 palettes; enemy SoRR colors calibrated onto BK3 indices; index 0 transparent'},indent=2))
    print('Prepared',len(entries),'frames;',len(atlas),'atlas bytes')
if __name__=='__main__':main()
