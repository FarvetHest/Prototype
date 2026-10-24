"""Independently verify combat audit records against the pinned BK3 listing."""
from pathlib import Path
import re,json,hashlib
p=Path(__file__).resolve().parents[1];raw=(p/'original/vendor/BK3.asm').read_bytes();ls=raw.decode(errors='replace').splitlines();labels={m[1]:i for i,l in enumerate(ls)if(m:=re.match(r'^(\w+):',l))}
def num(s):return int(s[1:],16)if s.startswith('$')else int(s)
def tokens(label,n):
 out=[]
 for l in ls[labels[label]:]:
  m=re.search(r'dc\.([bwl])\s+([^;]+)',l)
  if m:out.extend((m[1],v.strip())for v in m[2].split(','))
  if len(out)>=n:return out[:n]
 raise ValueError(label)
def verify(script,axel):
 rows=script['frames'];label=script.get('source_label',script.get('label'));stride=7 if axel else 4;t=tokens(label,1+len(rows)*stride)
 assert num(t[0][1])==len(rows),label
 for i,r in enumerate(rows):
  row=t[1+i*stride:1+(i+1)*stride]
  assert (num(row[0][1]),row[1][1],num(row[2][1]),num(row[3][1]))==(r['ticks'],r['mapping'],r['collision'],r['damage']),(label,i)
 return len(rows)
checks={};ref=json.loads((p/'assets/bk3-reference.json').read_text());count=0
for script in ref['scripts'].values():count+=verify(script,True)
checks['all_Axel_selected_ticks_damage_collision_from_ROM']=True
for family in json.loads((p/'assets/enemy-rom-match.json').read_text()).values():
 for script in family.values():count+=verify(script,False)
checks['all_Garcia_Donovan_selected_ticks_damage_collision_from_ROM']=True
for family in json.loads((p/'assets/enemy-variety.json').read_text())['types'].values():
 for script in family['scripts'].values():count+=verify(script,False)
checks['all_Electra_Zack_selected_ticks_damage_collision_from_ROM']=True
checks['own_sound_ID_table']=[num(v)for k,v in tokens('word_26264',6)]==[0x1c,0xce,0xda,0xd0,0xde,0xf6]
checks['special_effect_table_rows']=[num(v)for k,v in tokens('word_3082',13)][11:]==[0x5d4,0x5d4] and [num(v)for k,v in tokens('word_309C',13)][11:]==[12,12]
checks['source_special_guard_skips_HP_subtraction']='bne.w\tloc_25896' in '\n'.join(ls[labels['loc_257B2']:labels['loc_257D0']])
ai=(p/'src/ai.c').read_text();checks['attack_selection_has_no_slot_parity']='i&1'not in ai and 'i & 1'not in ai
# Existing ROM-derived profiles and geometry, independently read instead of regenerating with the importer.
checks['all_11_Garcia_AI_profiles']=ref['ai_profiles']==[num(v)for k,v in tokens('byte_2642A',352)]
checks['all_27_Axel_attack_rectangles']=ref['attack_boxes']==[num(v)for k,v in tokens('byte_4C4F0',216)]
for key,label,n,start,end in [('front_offsets','word_24B46',7,0,7),('back_offsets','word_24D5E',7,0,7),('front_release','word_24B70',28,12,16),('back_release','dword_24AE6',14,6,8)]:
 checks[key+'_ROM_exact']=ref[key]==[num(v)for k,v in tokens(label,n)][start:end]
result=dict(checks=checks,records=count,source_sha256=hashlib.sha256(raw).hexdigest(),note='Selected supported unarmed records only. Does not claim all ROM enemy handlers, weapons, cooperative/PvP or stage hazards are ported.')
(p/'test-results/combat-source-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
