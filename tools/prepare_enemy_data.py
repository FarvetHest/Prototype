"""Write source enemy scripts; run match_enemy_frames.py first."""
from pathlib import Path
import json
p=Path(__file__).resolve().parents[1];r=json.loads((p/'assets/enemy-rom-match.json').read_text())
keys=['idle','walk','held','hurt2','hurt','flight','floor','getup','front','back','jab','uppercut','kick']
h=['/* Generated from pinned BK3 scripts and reconstructed native poses. */']
for family in r:
 for name,script in r[family].items():h+=['static const EnemyFrame '+family+'_'+name+'[]={']+['{%d,%d,%d,%d,%d},'%(f['ticks'],f['fpg'],f['hurt'],f['collision'],f['damage'])for f in script['frames']]+['};']
h+=['static const EnemyFrame *const enemy_sequences[2][13]={']
for family in r:h+=['{'+','.join(family+'_'+(k if k in r[family]else'jab')for k in keys)+'},']
h+=['};','static const unsigned char enemy_sizes[2][13]={']
for family in r:h+=['{'+','.join(str(len(r[family][k if k in r[family]else'jab']['frames']))for k in keys)+'},']
h+=['};'];(p/'src/enemy_data.h').write_text('\n'.join(h)+'\n')
