"""Decode local original OGG once on the computer, without resampling or gain.
Requires soundfile (libsndfile). Runtime streams signed 16-bit stereo WAV.
"""
import argparse,hashlib,json,wave
from pathlib import Path
import soundfile as sf
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);a=ap.parse_args()
p=Path(__file__).resolve().parents[1];dest=p/'music.wav'
with sf.SoundFile(a.source) as src:
 assert src.samplerate==44100 and src.channels==2
 frames=0
 with wave.open(str(dest),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100)
  while True:
   data=src.buffer_read(16384,dtype='int16')
   if not data:break
   frames+=len(data)//4;w.writeframesraw(data)
with wave.open(str(dest),'rb') as w:
 raw=w.readframes(w.getnframes());assert w.getnframes()==frames
result=dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),wav_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),pcm_sha256=hashlib.sha256(raw).hexdigest(),rate=44100,channels=2,sample_bits=16,frames=frames,decoder='libsndfile via soundfile; no resampling, no gain')
(p/'assets/music-manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
