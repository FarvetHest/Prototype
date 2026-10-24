"""Pinned BK3 Axel electrical/held poses and Blondie guard/counter adaptation."""
from pathlib import Path
import argparse,sys,json,re,hashlib,types
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);a=ap.parse_args()
p=Path(__file__).resolve().parents[1]
assert hashlib.sha256(a.asm.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
# Reuse the independently checked native Axel tile renderer and palette mapping.
sys.argv=['prepare_pickup','--asm',str(a.asm),'--data',str(a.data)]
src=(p/'tools/prepare_pickup.py').read_text();ns={'__file__':str(p/'tools/prepare_pickup.py')};exec(src[:src.index("pix={(-x-1,y)")],ns)
num=ns['number'];render=ns['render'];mapping=ns['mapping'];dat=ns['dat']
base=(p/'tools/match_enemy_frames.py').read_text();en=dict(a=types.SimpleNamespace(asm=a.asm),re=re,hashlib=hashlib)
exec(base[base.index('ls=a.asm'):base.index("art=nemesis(dat(")],en);exec(base[base.index('def norm('):base.index('sets={')],en)
tokens=en['tokens'];number=en['num'];report={};frames={}
for label,ids in [('DMA_Axel_Electricuted',[920,921]),('DMA_Axel_Headlock',[922]),('DMA_Axel_PartnerBackGrab',[923])]:
 n=number(tokens(label,1)[0][1]);rows=tokens(label,1+n*7)[1:];assert n==len(ids);sc=[]
 for j,id in enumerate(ids):
  row=rows[j*7:j*7+7];regs=[number(v)for k,v in row[4:]];pix={(-x-1,y):mapping[c]for (x,y),c in render(row[1][1],regs).items()}
  x=min(x for x,y in pix);y=min(y for x,y in pix);w=max(xx for xx,yy in pix)-x+1;h=max(yy for xx,yy in pix)-y+1;buf=bytearray(w*h)
  for (xx,yy),v in pix.items():buf[(yy-y)*w+xx-x]=v
  frames[id]=dict(w=w,h=h,pivot=[-x,-y],pixels=buf.hex(),title=label+' / '+row[1][1]);sc.append(dict(ticks=number(row[0][1]),fpg=id,mapping=row[1][1],art=regs))
 report[label]=sc
(p/'assets/reaction-native.json').write_text(json.dumps(dict(frames=frames,source_sha256=hashlib.sha256(a.asm.read_bytes()).hexdigest(),scripts=report),indent=2))
native=json.loads((p/'assets/enemy-native.json').read_text());z=native['zack'];en['art']=en['nemesis'](en['dat']('ArtNem_GoldieZack'))
known={v['title']:int(k)for k,v in z['frames'].items()};nextid=max(known.values())+1;headers=[]
for name,mode in [('guard',6),('counter',76),('holder',8),('backholder',10)]:
 label=tokens(('AniScript_Zack_'if name in ('holder','backholder')else'AniScript_Blondie_')+format(mode,'X'),1)[0][1].split('-')[0];n=number(tokens(label,1)[0][1]);rows=tokens(label,1+n*4)[1:];sc=[]
 for j in range(n):
  row=rows[j*4:j*4+4];label2=row[1][1]
  if label2 not in known:
   known[label2]=nextid;nextid+=1;pix=en['render_pixels'](label2);x=min(x for x,y in pix);y=min(y for x,y in pix);w=max(xx for xx,yy in pix)-x+1;h=max(yy for xx,yy in pix)-y+1;buf=bytearray(w*h)
   for (xx,yy),v in pix.items():buf[(yy-y)*w+xx-x]=v
   z['frames'][str(known[label2])]=dict(w=w,h=h,pivot=[-x,-y],pixels=buf.hex(),title=label2)
  sc.append(dict(ticks=number(row[0][1]),fpg=known[label2],hurt=number(tokens(label2,2)[1][1]),collision=number(row[2][1]),damage=number(row[3][1])))
 report[('Zack_'if name in ('holder','backholder')else'Blondie_')+name]=dict(label=label,frames=sc)
 headers+=['static const EnemyFrame defense_'+name+'[]={']+['{%d,%d,%d,%d,%d},'%(f['ticks'],f['fpg'],f['hurt'],f['collision'],f['damage'])for f in sc]+['};']
for key,label in [('counter_boxes','byte_4CE50'),('counter_hurt','byte_4CC88')]:
 raw=en['dat'](label);assert len(raw)%8==0;headers+=['static const signed char '+key+'[][8]={']+['{'+','.join(str(v if v<128 else v-256)for v in raw[j:j+8])+'},'for j in range(0,len(raw),8)]+['};']
(p/'src/reaction_data.h').write_text('\n'.join(headers)+'\n')
(p/'assets/enemy-native.json').write_text(json.dumps(native))
(p/'assets/reaction-source.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(a.asm.read_bytes()).hexdigest(),scripts=report,scope='Zack captures from sub_2C2E8/2C80E/2C8BA/2C91A; guard/counter deliberately adapted from Obj_Blondie sub_2BEEE/2C990, not native Obj_Zack behavior'),indent=2))
print('Player new poses',len(frames),'Zack poses total',len(z['frames']))
