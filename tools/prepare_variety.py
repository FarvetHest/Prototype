from pathlib import Path
import sys,re,json,hashlib,collections,types
import argparse
p=Path(__file__).resolve().parents[1];sys.path.insert(0,str(p/'tools'))
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);args=ap.parse_args()
from prepare_sprites import decode,png
asm=args.asm;data=args.data
assert hashlib.sha256(asm.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
base=(p/'tools/match_enemy_frames.py').read_text()
ns=dict(a=types.SimpleNamespace(asm=asm),re=re,hashlib=hashlib)
exec(base[base.index('ls=a.asm'):base.index("art=nemesis(dat(")],ns)
exec(base[base.index('def norm('):base.index('sets={')],ns)
tokens,dat,num=ns['tokens'],ns['dat'],ns['num']
result={};native=json.loads((p/'assets/enemy-native.json').read_text());headers=[]
for name,file,artlabel,hurt,hit,profile,count in [('electra','electra','ArtNem_Electra','byte_4D7F8','byte_4D930','byte_2B0CC',7),('zack','gold','ArtNem_GoldieZack','byte_4CC58','byte_4CE30','byte_2C0F6',11)]:
 ns['art']=ns['nemesis'](dat(artlabel));palette,fpg=decode(data/(file+'.fpg'))
 shapes={i:ns['norm']({(k%f['w'],k//f['w'])for k,v in enumerate(f['pixels'])if v})for i,f in fpg.items()if any(f['pixels'])}
 scripts={};votes=[collections.Counter()for _ in range(16)];seen=set()
 modes={'idle':0,'walk':2,'held':12,'hurt2':16,'hurt':18,'flight':20,'floor':22,'getup':24,'front':36,'back':38,'jab':72,'uppercut':74,'kick':76,'jump':4,'guard':6}
 for key,mode in modes.items():
  ptr=tokens('AniScript_'+name.capitalize()+'_'+format(mode,'X'),1)[0][1].split('-')[0]
  n=num(tokens(ptr,1)[0][1]);rows=tokens(ptr,1+n*4)[1:];frames=[]
  assert 0<n<100,(name,key,n)
  for j in range(n):
   row=rows[j*4:j*4+4];mapping=row[1][1];pix=ns['render_pixels'](mapping);shape=ns['norm'](pix)
   score,fid=max((len(shape&s)/len(shape|s),fid)for fid,s in shapes.items());fr=fpg[fid]
   if mapping not in seen and score>.35:
    seen.add(mapping);x0=min(x for x,y in pix);y0=min(y for x,y in pix)
    fp={(k%fr['w'],k//fr['w']):v for k,v in enumerate(fr['pixels'])if v};fx=min(x for x,y in fp);fy=min(y for x,y in fp)
    for (x,y),v in pix.items():
     idx=fp.get((x-x0+fx,y-y0+fy),0)
     if idx:votes[v][idx]+=1
   frames.append(dict(ticks=num(row[0][1]),mapping=mapping,hurt=num(tokens(mapping,2)[1][1]),collision=num(row[2][1]),damage=num(row[3][1]),fpg=fid,iou=score))
  scripts[key]=dict(label=ptr,mode=mode,frames=frames)
 mappings=sorted({f['mapping']for sc in scripts.values()for f in sc['frames']});ids={m:1000+j for j,m in enumerate(mappings)};poses={}
 for mapping,fid in ids.items():
  pix=ns['render_pixels'](mapping);x=min(x for x,y in pix);y=min(y for x,y in pix);w=max(xx for xx,yy in pix)-x+1;h=max(yy for xx,yy in pix)-y+1;buf=bytearray(w*h)
  for (xx,yy),v in pix.items():buf[(yy-y)*w+xx-x]=v
  poses[fid]=dict(w=w,h=h,pivot=[-x,-y],pixels=buf.hex(),title=mapping)
 for sc in scripts.values():
  for f in sc['frames']:f['sorr_fpg']=f['fpg'];f['fpg']=ids[f['mapping']]
 cram=[num(v)for k,v in tokens('Pal_MainPal',16)]
 colors=[(round((v&14)*255/14),round(((v>>4)&14)*255/14),round(((v>>8)&14)*255/14),255 if j else 0)for j,v in enumerate(cram)]
 used={v for f in poses.values()for v in bytes.fromhex(f['pixels'])}
 print(name,'best match',max(f['iou'] for sc in scripts.values() for f in sc['frames']),'unmapped',[v for v in used if v and not votes[v]])
 native[name]=dict(palette=colors,frames=poses,source_art=artlabel,source_sha256=hashlib.sha256(asm.read_bytes()).hexdigest(),color_note='Native BK3 indices, pivots and Pal_MainPal CRAM, linear 3-bit expansion',palette_label='Pal_MainPal',cram=cram)
 # Collision dispatch indexed by object type/2 in original tables.
 actualhurt=tokens('Data_Hit_Collision',16)[14 if name=='electra' else 15][1]
 actualhit=tokens('Data_Atk_Collision',16)[14 if name=='electra' else 15][1]
 assert actualhurt==hurt and actualhit==hit,(actualhurt,actualhit)
 def table(label):return [list(dat(label)[i:i+8])for i in range(0,len(dat(label)),8)]
 hb,ab=table(hurt),table(hit);assert all(len(r)==8 for r in hb+ab)
 prof=[num(v)for k,v in tokens(profile,32*count)];assert len(prof)==32*count
 result[name]=dict(scripts=scripts,hurt_boxes=hb,attack_boxes=ab,profile_label=profile,profiles=[prof[j:j+32]for j in range(0,len(prof),32)],art_bytes=len(ns['art']))
 print(name,len(poses),'poses',[(k,len(v['frames']),[(f['collision'],f['damage'])for f in v['frames']if f['damage']])for k,v in scripts.items()])
(p/'assets/enemy-native.json').write_text(json.dumps(native))
(p/'assets/enemy-variety.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(asm.read_bytes()).hexdigest(),types=result),indent=2))
for name,r in result.items():
 for k,sc in r['scripts'].items():headers+=['static const EnemyFrame '+name+'_'+k+'[]={']+['{%d,%d,%d,%d,%d},'%(f['ticks'],f['fpg'],f['hurt'],f['collision'],f['damage'])for f in sc['frames']]+['};']
 for key in ['hurt_boxes','attack_boxes','profiles']:
  ctype='unsigned char' if key=='profiles' else 'signed char';rows=r[key]
  headers+=['static const '+ctype+' '+name+'_'+key+'['+str(len(rows))+']['+str(len(rows[0]))+']={']+['{'+','.join(str(v if ctype=='unsigned char' or v<128 else v-256)for v in row)+'},'for row in rows]+['};']
(p/'src/variety_data.h').write_text('\n'.join(headers)+'\n')
