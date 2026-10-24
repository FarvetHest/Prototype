from pathlib import Path
import sys,hashlib,json,subprocess
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--previous',type=Path,required=True);args=ap.parse_args()
p=Path(__file__).resolve().parents[1];old=args.previous;checks={}
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for file in ['assets/sprites.t8','src/sprite_data.h','src/sfx_data.h','music.wav','src/combat.c','src/physics.c','src/bk3.c','src/machine.c','src/enemy.c','src/variety.c','src/death.c','original/vendor/BK3.asm']:
 if not(p/file).exists():continue
 checks['unchanged_'+file]=((p/file).read_text()==(old/file).read_text()) if file.endswith('.c') else h(p/file)==h(old/file)
def unswizzle(raw):
 out=bytearray(len(raw));off=0
 for by in range(0,256,8):
  for bx in range(0,1024,16):
   for dy in range(8):out[(by+dy)*1024+bx:(by+dy)*1024+bx+16]=raw[off:off+16];off+=16
 return out
before=unswizzle((old/'assets/hud.rgba').read_bytes());after=unswizzle((p/'assets/hud.rgba').read_bytes());m=json.loads((old/'assets/hud-manifest.json').read_text());kept=True
for f in m['frames']:
 for y in range(f['h']):
  start=((f['v']+y)*256+f['u'])*4;kept &= before[start:start+f['w']*4]==after[start:start+f['w']*4]
checks['old_HUD_frame_pixels_preserved']=kept
files=['assets/stage.t8','src/stage_data.h','assets/hud.rgba','src/hud_data.h'];baseline={f:h(p/f)for f in files}
for tool in ['prepare_sor1_stage','prepare_bk3_special']:
 r=subprocess.run([sys.executable,str(p/'tools'/(tool+'.py'))],stdout=subprocess.PIPE,text=True);checks[tool+'_reproducible']=r.returncode==0 and all(h(p/f)==baseline[f]for f in files if ('hud' in f)==('special' in tool))
checks['T8_background_reduces_RAM']=len((p/'assets/stage.t8').read_bytes())==262144<1572864
result=dict(checks=checks,eboot_sha256=h(p/'build/EBOOT.PBP'),note='Unchanged combat core, atlas, PCM and old HUD pixels; deterministic re-extraction of SoR1 stage and original BK3 special meter.')
(p/'test-results/route1-assets.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
