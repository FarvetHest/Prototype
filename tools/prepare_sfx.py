"""Embed the user's confirmed SoRR impact sample; music remains untouched."""
from pathlib import Path
import argparse,wave,struct,json,hashlib,shutil
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);a=ap.parse_args();p=Path(__file__).resolve().parents[1]
with wave.open(str(a.source),'rb')as w:
 assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==44100
 raw=w.readframes(w.getnframes());values=struct.unpack('<%dh'%(len(raw)//2),raw)
assert 0<len(values)<44100
# Remove boundary clicks and leave headroom for the independent music channel.
peak=max(abs(v)for v in values);out=[]
for i,v in enumerate(values):out.append(round(v*14000/max(peak,1)*min(1,i/32,(len(values)-1-i)/32)))
shutil.copy2(a.source,p/'assets/impact-source.wav')
(p/'src/sfx_data.h').write_text('/* Prepared once from the local SoRR impact WAV. */\nstatic const short sfx_sample[]={\n'+','.join(map(str,out))+'\n};\n#define SFX_FRAMES '+str(len(out))+'\n')
(p/'assets/sfx-manifest.json').write_text(json.dumps(dict(source=a.source.name,source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),rate=44100,channels=1,frames=len(out),pcm_sha256=hashlib.sha256(struct.pack('<%dh'%len(out),*out)).hexdigest(),peak=max(abs(v)for v in out),processing='peak headroom14000,32-sample boundary fade; no resampling',mapping='BK3 damage thresholds select sound IDs18/26/21/32 hex; single SoRR impact timbre at four gains; floor346 hex'),indent=2))
print('Prepared impact:',len(out),'frames, peak',max(abs(v)for v in out))
