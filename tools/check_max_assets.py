"""Check Max extraction independently against original remaining-frame tables."""
from pathlib import Path
import json,hashlib,re,subprocess,sys,struct
p=Path(__file__).resolve().parents[1];m=json.loads((p/'assets/max-sor2-source.json').read_text());raw=(p/'original/vendor/SOR2.asm').read_bytes();ls=raw.decode(errors='replace').splitlines();labels={x[1]:i for i,l in enumerate(ls)if(x:=re.match(r'^(\w+):',l))}
def block(n):
 i=labels[n];j=i+1
 while j<len(ls)and not re.match(r'^\w+:',ls[j]):j+=1
 return '\n'.join(ls[i:j])
def num(v):return int(v[1:],16)if v.startswith('$')else int(v)
def bytes_at(n):
 out=bytearray()
 for typ,vals in re.findall(r'dc\.([bwl])\s+([^;\n]+)',block(n)):
  for v in vals.split(','):
   z={'b':1,'w':2,'l':4}[typ];out.extend((num(v.strip())&((1<<(z*8))-1)).to_bytes(z,'big'))
 return out
checks={};checks['pinned_ROM_listing']=hashlib.sha256(raw).hexdigest()==m['source_sha256']=='30f9c07ff55b85dd53083fe9b0a828faa3fb4600a0ac54dfc5f2d432265da274'
# The original Get_AttackCollisionData uses (remaining FrameID-1)*4.
for anim,rows in m['scripts'].items():
 anim=int(anim)
 if anim<0x30 or anim==0x54:continue
 table='AttackCollision_Max'if anim==0x30 else'word_%X'%(0x2400+anim-0x30)
 cm=re.search(r'dc\.w\s+(byte_\w+)-',block(table))if table in labels else None
 coll=bytes_at(cm[1])if cm else None
 for j,r in enumerate(rows):
  src=coll[(len(rows)-1-j)*4:(len(rows)-j)*4]if coll else bytes(4)
  assert len(src)==4
  width=(src[0]-256 if src[0]&128 else src[0])*2;height=src[1]-256 if src[1]&128 else src[1]
  assert (r['width'],r['height'],r['damage'],r['sound'])==(width,height,src[2],src[3]),(hex(anim),j)
checks['all_attack_records_use_remaining_FrameID']=True
checks['original_combo_timers']=[r['ticks']for r in m['scripts']['58']]==[3,3,3,8] and [r['ticks']for r in m['scripts']['60']]==[3,3,6,8,5]
checks['atomic_damage_seven_bits']=m['scripts']['82'][0]['damage']==0xc6 and (m['scripts']['82'][0]['damage']&127)==70
checks['43_original_scripts_80_poses_plus_6_run_poses']=len(m['scripts'])==44 and m['frame_count']==86 and sum(e['id']<1100 for e in m['frames'])==80
checks['atlas_RAM_3_pages']=m['atlas_bytes']==786432 and m['atlas_pages']==3 and len((p/'assets/max.t8').read_bytes())==786432
checks['atlas_hash']=hashlib.sha256((p/'assets/max.t8').read_bytes()).hexdigest()==m['atlas_sha256']
checks['no_page_crossing']=all(e['u']+e['w']<=512 and e['v']//512==(e['v']+e['h'])//512 for e in m['frames'])
checks['all_script_poses_exist']=all(r['fpg']in{e['id']for e in m['frames']}for rows in m['scripts'].values()for r in rows)
base=json.loads((p/'assets/v0241-combat-baseline.json').read_text())
checks['Axel_enemy_stage_music_assets_unchanged']=all(hashlib.sha256((p/f).read_bytes()).hexdigest()==sha for f,sha in base['unchanged_files'].items())
checks['original_43_Max_scripts_unchanged']=all(m['scripts'][k]==v for k,v in base['Max_original_scripts'].items())
checks['original_80_Max_pixel_hashes_unchanged']=all(base['Max_original_pixel_hashes'][str(e['id'])]==e['pixel_sha256'] for e in m['frames']if e['id']<1100)
checks['original_eight_sound_clips_unchanged']=json.loads((p/'assets/sfx-manifest.json').read_text())['clips'][:8]==base['original_eight_sfx_clips']
checks['run_source_frames']=m['run_extension']['source_frames']==list(range(168,174)) and m['run_extension']['source_sha256']==hashlib.sha256((p/'original/max.fpg').read_bytes()).hexdigest()
# Regenerate the actual assets to check deterministic extraction, pixels and maps.
files=['src/max_data.h','src/max_sor2_data.h','assets/max.t8','assets/max-sor2-source.json','assets/max-contact.png']
before={f:hashlib.sha256((p/f).read_bytes()).hexdigest()for f in files}
subprocess.run([sys.executable,str(p/'tools/prepare_max_sor2.py'),'--asm',str(p/'original/vendor/SOR2.asm')],check=True)
checks['deterministic_original_extraction']=before=={f:hashlib.sha256((p/f).read_bytes()).hexdigest()for f in files}
result=dict(checks=checks,eboot_sha256=hashlib.sha256((p/'build/EBOOT.PBP').read_bytes()).hexdigest(),source_sha256=m['source_sha256'])
(p/'test-results/max-assets.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
