from pathlib import Path
import sys,json,hashlib,subprocess
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'tools'))
from prepare_sprites import decode
source=P/'original/max.fpg';pal,frames=decode(source);m=json.loads((P/'assets/max-manifest.json').read_text());raw=(P/'assets/max.t8').read_bytes();linear=bytearray(len(raw));o=0
for by in range(0,m['atlas_pages']*512,8):
 for bx in range(0,512,16):
  for dy in range(8):linear[(by+dy)*512+bx:(by+dy)*512+bx+16]=raw[o:o+16];o+=16
checks={};checks['source_pin']=hashlib.sha256(source.read_bytes()).hexdigest()==m['source_sha256'];checks['original_palette']=list(map(list,pal))==m['palette']
checks['all_pixels_and_control_points']=all(bytes().join(linear[(f['v']+y)*512+f['u']:(f['v']+y)*512+f['u']+f['w']]for y in range(f['h']))==frames[f['id']]['pixels'] and [f['px'],f['py']]==list(frames[f['id']]['pivot'])for f in m['frames'])
checks['no_frame_crosses_page']=all(f['v']//512==(f['v']+f['h']-1)//512 for f in m['frames'])
old=json.loads((P/'assets/manifest.json').read_text());checks['every_player_pose_has_alias']=all(str(f['id'])in m['aliases']for f in old['frames']if f['family']==0)
checks['aliases_are_real_Max_frames']=set(m['aliases'].values())<=set(f['id']for f in m['frames'])
base=P.parent/'SoRR-PSP-Lite-v0.22';checks['Axel_and_enemies_atlas_unchanged']=(P/'assets/sprites.t8').read_bytes()==(base/'assets/sprites.t8').read_bytes();checks['native_stage_unchanged']=(P/'assets/stage.t8').read_bytes()==(base/'assets/stage.t8').read_bytes();checks['original_sfx_unchanged']=(P/'src/sfx_data.h').read_bytes()==(base/'src/sfx_data.h').read_bytes();checks['music_unchanged']=(P/'music.wav').read_bytes()==(base/'music.wav').read_bytes()
checks['HD_Floyd_not_in_project']=not any('floyd' in f.name.lower() for folder in ['src','assets','original']for f in(P/folder).rglob('*')if f.is_file())
files=['assets/max.t8','src/max_data.h','assets/hud.rgba','src/hud_data.h'];before={f:hashlib.sha256((P/f).read_bytes()).hexdigest()for f in files};r=subprocess.run([sys.executable,str(P/'tools/prepare_max.py')],check=True);checks['extraction_reproducible']=all(hashlib.sha256((P/f).read_bytes()).hexdigest()==before[f]for f in files)
report=dict(checks=checks,eboot_sha256=hashlib.sha256((P/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Original Max FPG indices, palette and pivots preserved byte-for-byte; no HD or manual limb assembly. Base-version comparison needs sibling v0.22.')
(P/'test-results/max-assets.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert all(checks.values())
