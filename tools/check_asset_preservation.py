from pathlib import Path
import json,hashlib,struct
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--previous',type=Path,required=True,help='v0.20 project/checkout for the 210 prior-pose comparisons');args=ap.parse_args()
p=Path(__file__).resolve().parents[1];old=args.previous
m=json.loads((p/'assets/manifest.json').read_text());om=json.loads((old/'assets/manifest.json').read_text());data=(p/'assets/sprites.t8').read_bytes();od=(old/'assets/sprites.t8').read_bytes();native=json.loads((p/'assets/enemy-native.json').read_text());entries={(f['family'],f['id']):f for f in m['frames']}
def crop(a,f):
 out=bytearray()
 for y in range(f['y'],f['y']+f['h']):
  for x in range(f['x'],f['x']+f['w']):
   page,v=divmod(y,512);out.append(a[page*262144+((v//8)*32+x//16)*128+(v%8)*16+x%16])
 return bytes(out)
checks={}
checks['all_210_previous_poses_pixels_pivots_unchanged']=all(all(entries[f['family'],f['id']][k]==f[k]for k in ['w','h','px','py'])and crop(data,entries[f['family'],f['id']])==crop(od,f)for f in om['frames'])
for family,name in [(3,'electra'),(4,'zack'),(5,'barbon')]:
 n=native[name];exact=True
 for key,v in n['frames'].items():
  f=entries[family,int(key)];raw=bytes.fromhex(v['pixels']);cropped=b''.join(raw[(y+f['crop_top'])*v['w']+f['crop_left']:(y+f['crop_top'])*v['w']+f['crop_left']+f['w']]for y in range(f['h']))
  exact &= crop(data,f)==cropped and [f['px'],f['py']]==[v['pivot'][0]-f['crop_left'],v['pivot'][1]-f['crop_top']]
 checks[name+'_all_native_pixels_pivots']=exact
 checks[name+'_original_CRAM']=n['palette_label']==('Pal_Barbon'if name=='barbon'else'Pal_MainPal')and len(n['palette'])==16 and all(color==[((v&14)*255//14 if name=='barbon'else round((v&14)*255/14)),(((v>>4)&14)*255//14 if name=='barbon'else round(((v>>4)&14)*255/14)),(((v>>8)&14)*255//14 if name=='barbon'else round(((v>>8)&14)*255/14)),255 if j else 0]for j,(v,color)in enumerate(zip(n['cram'],n['palette'])))
reaction=json.loads((p/'assets/reaction-native.json').read_text())
checks['four_player_reaction_poses_exact']=all(crop(data,entries[0,int(key)])==bytes.fromhex(v['pixels']) and [entries[0,int(key)]['px'],entries[0,int(key)]['py']]==v['pivot']for key,v in reaction['frames'].items())
checks['246_frames_five_pages']=len(entries)==246 and len(data)==1310720
checks['no_frame_crosses_a_page']=all(f['y']//512==(f['y']+f['h']-1)//512 for f in entries.values())
for name in ['stage.rgb565','hud.rgba']:
 checks[name+'_unchanged']=(p/'assets'/name).read_bytes()==(old/'assets'/name).read_bytes()
checks['music_unchanged']=(p/'music.wav').read_bytes()==(old/'music.wav').read_bytes()
checks['full_atlas_embedded']=data in (p/'build/sorr-lite.elf').read_bytes()
checks['three_VRAM_two_RAM_pages']='(f->v/512<3?(const unsigned char *)texture_vram:sprite_atlas)'in(p/'src/sprites.c').read_text()
result=dict(checks=checks,eboot_sha256=hashlib.sha256((p/'build/EBOOT.PBP').read_bytes()).hexdigest(),atlas_sha256=hashlib.sha256(data).hexdigest(),old_poses=210,new_poses=36,vram_resident_atlas_bytes=786432,extra_RAM_atlas_bytes=524288)
(p/'test-results/food-assets.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
