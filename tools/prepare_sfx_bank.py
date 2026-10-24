"""Embed unmodified original SoRR SoR3 impact WAVs; no DSP or resampling."""
from pathlib import Path
import argparse,wave,struct,json,hashlib,shutil,math
ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);a=ap.parse_args();p=Path(__file__).resolve().parents[1]
settings=[('light',0x18,'seg1.wav'),('medium',0x26,'seg2.wav'),('heavy',0x21,'seg3.wav'),('crush',0x32,'se53.wav'),('floor',0x346,'se45.wav'),('male1',0x20a,'sev1.wav'),('male2',0x20b,'sev2.wav'),('female',0x217,'seblaze1.wav')]
clips=[];header=['/* Unmodified original SoRR PCM; see assets/sfx-manifest.json. */'];preview=[]
for name,id,filename in settings:
 source=a.data/filename
 with wave.open(str(source),'rb')as w:
  assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,44100)
  pcm=w.readframes(w.getnframes());n=w.getnframes();out=struct.unpack('<%dh'%n,pcm)
 assert 0<n<88200
 target=p/'assets'/('impact-'+name+'.wav')
 if target.resolve()!=source.resolve():shutil.copy2(source,target)
 assert target.read_bytes()==source.read_bytes()
 header+=['static const short sfx_'+name+'[]={']+[','.join(map(str,out[j:j+64]))+',' for j in range(0,n,64)]+['};']
 clips.append(dict(name=name,id=id,source=filename,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),frames=n,peak=max(map(abs,out)),rms=round(math.sqrt(sum(v*v for v in out)/n),2),pcm_sha256=hashlib.sha256(pcm).hexdigest()))
 if len(clips)<=5:preview.extend(out);preview.extend([0]*11025)
header+=['typedef struct { const short *pcm; int frames; } SfxClip;','static const SfxClip sfx_clips[]={']+[' {sfx_%s,%d},'%(c['name'],c['frames'])for c in clips]+['};','#define SFX_CLIP_COUNT '+str(len(clips)),'#define SFX_FRAMES '+str(clips[0]['frames']),'']
(p/'src/sfx_data.h').write_text('\n'.join(header))
with wave.open(str(p/'assets/impact-strength-preview.wav'),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(struct.pack('<%dh'%len(preview),*preview))
(p/'assets/sfx-manifest.json').write_text(json.dumps(dict(source='Unmodified local SoRR 5.2 WAV files, SoR3 impact set',mapping_reference='https://sorr.forumotion.net/t263-sound-effect-modding-tutorial',rate=44100,channels=1,clips=clips,processing='NONE: WAV files copied byte-for-byte; embedded PCM identical to decoded originals. No pitch, normalization, filter, synthesized layers, trimming, fade or resampling.',mapping='18 seg1 light;26 seg2 strong;21 seg3 fierce;32 se53 EX;346 se45 floor;20A sev1 male death;20B sev2 male death;217 seblaze1 female death',mix='unity SFX output, average simultaneous voices; music duck180ms on impact, up to1200ms for death cries; baseline0x4000'),indent=2))
print(json.dumps(clips,indent=2))
