"""Extract raw BK3 animation timers/damage and collision bytes, with source provenance."""
import argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--asm',type=Path,required=True);a=ap.parse_args()
assert hashlib.sha256(a.asm.read_bytes()).hexdigest()=='ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3', 'Use the pinned BK3 listing (see source commit)'
p=Path(__file__).resolve().parents[1];lines=a.asm.read_text(encoding='utf-8',errors='replace').splitlines()
labels={m[1]:i for i,l in enumerate(lines)if(m:=re.match(r'^(\w+):',l))}
def num(x):return int(x[1:],16)if x.startswith('$')else int(x)
def tokens_at(name,count):
 out=[]
 for line in lines[labels[name]:]:
  m=re.search(r'\bdc\.([wbl])\s+([^;]+)',line)
  if m:out.extend((m[1],v.strip())for v in m[2].split(','))
  if len(out)>=count:break
 return out[:count]
def script(name):
 n=num(tokens_at(name,1)[0][1]);raw=tokens_at(name,1+n*7)[1:];out=[]
 for i in range(n):
  row=raw[i*7:i*7+7];assert ''.join(x[0]for x in row)=='wlbbwww'
  out.append(dict(ticks=num(row[0][1]),mapping=row[1][1],collision=num(row[2][1]),damage=num(row[3][1]),art=[num(v)for k,v in row[4:]]))
 return dict(source_label=name,line=labels[name]+1,frames=out)
names={'idle':'Standing','walk':'Walking','run':'Run','jump':'Jumping1','punch1':'Punch1','punch2':'Punch2','kick':'Kick1','blitz':'GrandUpper','air1':'Flykick1','air2':'Flykick2','special1':'Supermove1','special2':'Supermove2','frontgrab':'FrontGrab','backgrab':'BackGrab','headbutt':'Headbutt','knee':'KneeJab','jumpknee':'JumpingKneeJab','frontthrow':'FrontHoldThrow','backthrow':'BackHoldThrow','vault':'JumpOver','hit':'Hit1','knockout':'KnockedOut','lying':'LyingOnGround','getup':'GetUp','rolldown':'RollDown','rollup':'RollUp','backhand':'BackHand','doublekick':'DoubleKick'}
scripts={k:script('DMA_Axel_'+v)for k,v in names.items()}
# Explicit visual adapter: ROM mapping addresses are NOT FPG IDs.
mapping={}
def bind(key,ids):
 rows=scripts[key]['frames'];assert len(ids)==len(rows)
 for row,id in zip(rows,ids):
  old=mapping.setdefault(row['mapping'],id);assert old==id,(row,old,id)
bind('doublekick',[83,84,85,84,86,83]);bind('backhand',[14,15,16,17,15]);bind('idle',[1,2,3,4]*8+[32,33]);bind('walk',list(range(5,11)));bind('run',list(range(168,174)))
bind('jump',[60,12,13]);bind('punch1',[1,80]);bind('punch2',[1,81,82,81]);bind('kick',[83,84,85,83])
bind('blitz',[60,61,62,61,62,63,64,65,66,67]);bind('air1',[18,19,20,19,18,13]);bind('air2',[22,23])
bind('special1',list(range(24,32)));bind('special2',list(range(34,44))+list(range(34,43))+[44,45,46,53])
bind('frontgrab',[68]);bind('backgrab',[79]);bind('headbutt',[69,70,71]);bind('knee',[72]);bind('jumpknee',[72,100,73,100]);bind('frontthrow',[153,154,155,156,154]);bind('backthrow',[153,154,157,158,159,45,46,53]);bind('vault',[150,151,152,151,150]);bind('hit',[148,148,148,148]);bind('knockout',[49]);bind('lying',[50]);bind('getup',[51,50,51,53]);bind('rolldown',[60,99,98,53]);bind('rollup',[53,98,99,60])
for v in scripts.values():
 for row in v['frames']:row['fpg']=mapping[row['mapping']]
boxes=[num(v)for k,v in tokens_at('byte_4C4F0',27*8)];assert len(boxes)==216
walk=[num(v)for k,v in tokens_at('Data_Walk_Inertia',7)];run=[num(v)for k,v in tokens_at('Data_RunSpeed',7)];jump=[num(v)for k,v in tokens_at('dword_9780',7)]
result=dict(source_sha256=hashlib.sha256(a.asm.read_bytes()).hexdigest(),source_repository='https://github.com/gsaurus/sor-disassemblies',source_commit='4dd719f3ed5c24c86deee616b56cea885e3113d7',source_file=a.asm.name,scripts=scripts,walk_words=walk,run_words=run,jump_longs=jump,attack_boxes=boxes,mapping_note='FPG adapter selected visually; ROM timers, collision IDs and damage are extracted. Mapping checked against reconstructed ROM sprite silhouettes; see axel-rom-match.json. Some frames differ or have ambiguous matches.',scope='Axel movement, jumps, grabs, throws, specials; selected unarmed Garcia/Donovan behavior. Remaining adaptations documented in PORTING-NOTES.md.')
(p/'assets/bk3-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
h=['/* Generated from the pinned BK3 listing; see assets/bk3-reference.json. */','#ifndef BK3_DATA_H','#define BK3_DATA_H','typedef struct { unsigned short ticks,fpg; unsigned char collision,damage; } Bk3Frame;']
for key,v in scripts.items():
 h+=['static const Bk3Frame bk3_'+key+'[] = {']+['{%d,%d,%d,%d},'%(x['ticks'],x['fpg'],x['collision'],x['damage'])for x in v['frames']]+['};']
h+=['static const signed char bk3_attack_boxes[27][8]={']
for i in range(27):h+=['{'+','.join(str(x if x<128 else x-256)for x in boxes[i*8:i*8+8])+'},']
h+=['};',f'#define BK3_WALK_FP {walk[3]<<8}',f'#define BK3_RUN_FP {(run[3]<<8)*2}',f'#define BK3_JUMP_FP {jump[3]-2**32}', '#define BK3_GRAVITY_FP 16384','#define BK3_AIR_ACCEL_FP 16384','#define BK3_AIR_LIMIT_FP 131072','#define BK3_DOUBLE_TAP 16','#endif']
(p/'src/bk3_data.h').write_text('\n'.join(h)+'\n')
def enemy_script(name,ids):
 n=num(tokens_at(name,1)[0][1]);raw=tokens_at(name,1+n*4)[1:];out=[];assert n==len(ids)
 for i in range(n):
  row=raw[i*4:i*4+4];assert ''.join(x[0]for x in row)=='wlbb'
  out.append(dict(ticks=num(row[0][1]),mapping=row[1][1],collision=num(row[2][1]),damage=num(row[3][1]),fpg=ids[i]))
 return dict(source_label=name,line=labels[name]+1,frames=out)
enemy_scripts={'garcia_jab':enemy_script('word_203158',[18,17,4,17,18,1]),'donovan_jab':enemy_script('word_203A96',[1,5,5,4,5,5]),'donovan_uppercut':enemy_script('word_203AC8',[1,13,14,6,6,13]),'donovan_kick':enemy_script('word_203AFA',[1,10,11,23,12])}
profile=[num(v)for k,v in tokens_at('byte_2642A',352)]
front=[num(v)for k,v in tokens_at('word_24B46',7)];back=[num(v)for k,v in tokens_at('word_24D5E',7)]
front_release=[num(v)for k,v in tokens_at('word_24B70',28)][12:16];back_release=[num(v)for k,v in tokens_at('dword_24AE6',14)][6:8]
extra=dict(enemy_scripts=enemy_scripts,ai_profiles=profile,front_offsets=front,back_offsets=back,front_release=front_release,back_release=back_release)
result.update(extra);(p/'assets/bk3-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
ch=['/* Generated from the pinned BK3 listing; needs bk3_data.h. */','#ifndef COMBAT_DATA_H','#define COMBAT_DATA_H']
for key,v in enemy_scripts.items():
 ch+=['static const Bk3Frame '+key+'[]={']+['{%d,%d,%d,%d},'%(x['ticks'],x['fpg'],x['collision'],x['damage'])for x in v['frames']]+['};']
ch+=['static const unsigned char garcia_profiles[11][32]={']
for i in range(11):ch+=['{'+','.join(map(str,profile[i*32:i*32+32]))+'},']
ch+=['};']
for name,data in [('front_offsets',front),('back_offsets',back),('front_release',front_release),('back_release',back_release)]:ch+=['static const unsigned '+name+'[]={'+','.join(hex(x)+'u'for x in data)+'};']
for name,label,n in [('garcia_boxes','byte_4CD78',4),('donovan_boxes','byte_4CD98',5)]:
 data=[num(v)for k,v in tokens_at(label,n*8)];ch+=['static const signed char '+name+'['+str(n)+'][8]={']
 for i in range(n):ch+=['{'+','.join(str(v if v<128 else v-256)for v in data[i*8:i*8+8])+'},']
 ch+=['};']
ch+=['#endif'];(p/'src/combat_data.h').write_text('\n'.join(ch)+'\n')
print('Extracted',sum(len(v['frames'])for v in scripts.values()),'animation entries and',len(boxes)//8,'attack rectangles')
