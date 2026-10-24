"""Run against the Lite EBOOT in PPSSPP with its local remote debugger enabled.
Requires: python -m pip install websocket-client
Combat tests intentionally arrange actors through debugger memory writes.
"""
import argparse, os, subprocess, time, json, struct, base64, zlib, hashlib, math
from pathlib import Path
import websocket
ap=argparse.ArgumentParser()
ap.add_argument('--pspdev',type=Path,default=os.environ.get('PSPDEV'))
ap.add_argument('--url',default='ws://127.0.0.1:19876/debugger')
ap.add_argument('--soak-seconds',type=int,default=0)
args=ap.parse_args()
if not args.pspdev: ap.error('Set PSPDEV or supply --pspdev')
project=Path(__file__).resolve().parents[1]
artifacts=project/'test-results'
artifacts.mkdir(exist_ok=True)
class PSP:
    def __init__(self):
        self.ws=websocket.create_connection(args.url,subprotocols=['debugger.ppsspp.org'],timeout=15,suppress_origin=True)
        self.req('version',name='Lite integration tests',version='1')
        status=self.req('game.status');deadline=time.monotonic()+15
        while not status.get('game') and time.monotonic()<deadline:
            time.sleep(.1);status=self.req('game.status')
        if (status.get('game')or{}).get('id')!='SORL00024':
            raise RuntimeError('Load SoRR PSP Lite EBOOT first; refusing to modify another game')
        nm=args.pspdev/'bin'/('psp-nm.exe' if os.name=='nt' else 'psp-nm')
        raw=subprocess.check_output([str(nm),'-n',str(project/'build/sorr-lite.elf')],text=True)
        self.symbols={a[2]:int(a[0],16)+0x08804000 for l in raw.splitlines() if len(a:=l.split())==3 and all(c in '0123456789abcdefABCDEF' for c in a[0])}
    def req(self,event,**params):
        self.ws.send(json.dumps(dict(event=event,ticket=event,**params)))
        while True:
            r=json.loads(self.ws.recv())
            if r.get('ticket')==event or r.get('event')==event:
                if r.get('event')=='error':raise RuntimeError(r)
                return r
    def read(self,addr,size):return base64.b64decode(self.req('memory.read',address=addr,size=size)['base64'])
    def u32(self,s):return struct.unpack('<I',self.read(self.symbols[s],4))[0]
    def send(self,**buttons):return self.req('input.buttons.send',buttons=buttons)
    def close(self):self.ws.close()
p=PSP()
# Trace arrays are populated during startup selftests, before the first GU frame.
ready_deadline=time.monotonic()+15
while p.u32('frame_count')<2:
    if time.monotonic()>ready_deadline:raise RuntimeError('PSP startup did not reach rendering')
    time.sleep(.1)
checks={}
p.req('memory.write_u32',address=p.symbols['player_character'],value=1)
def state():
    raw=p.read(p.symbols['game'],192)
    return dict(player=list(struct.unpack_from('<2f7i',raw)), enemies=[list(struct.unpack_from('<2f7i',raw,36*(i+1))) for i in range(4)], ticks=struct.unpack_from('<I',raw,180)[0],paused=struct.unpack_from('<i',raw,184)[0],won=struct.unpack_from('<i',raw,188)[0])
def button(name,t=0.18):
    p.send(**{name:True});time.sleep(t);p.send(**{name:False});time.sleep(0.1)
def reset():
    p.send(ltrigger=True,rtrigger=True);time.sleep(0.15);p.send(ltrigger=False,rtrigger=False);time.sleep(0.12)
    p.req('memory.write_u32',address=p.symbols['level'],value=0)
    p.req('memory.write',address=p.symbols['level']+132,base64=base64.b64encode(bytes(96)).decode())
    # The stream opens with two actors; isolated legacy combat scenarios need four.
    for i in range(4):
        p.req('memory.write',address=p.symbols['game']+36*(i+1),base64=base64.b64encode(struct.pack('<2f7i',144.+i*23.,79.+i*12.,40,-1,20+i*9,0,0,0,0)).decode())
def frames():return list(struct.unpack('<5I',p.read(p.symbols['actor_frames'],20)))
def moves():return list(struct.unpack('<34i',p.read(p.symbols['game']+192,136)))

def music():return list(struct.unpack('<2i10I',p.read(p.symbols['music_stats'],48)))
def screenshot(path):
    p.req('cpu.stepping')
    try:
        raw=p.read(p.u32('presented_buffer'),512*272*2)
        rows=[]
        for y in range(272):
            row=bytearray(b'\0')
            for x in range(480):
                v=struct.unpack_from('<H',raw,y*1024+x*2)[0]
                row.extend(((v&31)*255//31,((v>>5)&63)*255//63,((v>>11)&31)*255//31))
            rows.append(row)
        def chunk(k,d): return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d))
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',480,272,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))
    finally:p.req('cpu.resume')
def arrange(hp,player_hp=100,attack=0,x=82.0,one=False):
    p.req('cpu.stepping')
    a=p.symbols['game']
    def put(off,fmt,*v):p.req('memory.write',address=a+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
    try:
        put(0,'<2f7i',64.,100.,player_hp,1,0,0,0,0,0)
        for i in range(4):put(36*(i+1),'<2f7i',x if not one or i==0 else 220.,100. if not one or i==0 else 120.,hp,-1,100,0,attack,0,0)
        put(184,'<2i',0,0);put(328,'<184s',bytes(184))
        cb=bytearray(288);struct.pack_into('<i',cb,12,-1);struct.pack_into('<i',cb,40,112);struct.pack_into('<I',cb,56,0xace1)
        for i in range(4):
            struct.pack_into('<i',cb,64+i*56+4,10000);struct.pack_into('<i',cb,64+i*56+16,5);struct.pack_into('<i',cb,64+i*56+32,1)
            if attack:
                struct.pack_into('<i',cb,64+i*56,9);struct.pack_into('<i',cb,64+i*56+20,3 if i%2 else 2);struct.pack_into('<i',cb,64+i*56+24,4)
            elif not one or i:put(36*(i+1)+20,'<i',10000)
        put(512,'<288s',cb);put(800,'<284s',bytes(284))
        rules=bytearray(404)
        for j in range(5):struct.pack_into('<12i',rules,j*48,6 if not j else 14 if j%2 else 16,128,0,0,0,0,8,0,-1,-1,0,1)
        for j in range(4):struct.pack_into('<10i',rules,240+j*40,0x1a if attack else 2,0,-1,0,0,0,0,0,0,0)
        put(1084,'<404s',rules);put(1488,'<176s',bytes(176))
        raw=bytearray(136);struct.pack_into('<i',raw,52,100);struct.pack_into('<i',raw,64,-1)
        p.req('memory.write',address=a+192,base64=base64.b64encode(raw).decode())
    finally:p.req('cpu.resume')
def render_snapshot():
 # Debugger reads while running can observe stage_draw_count just after its reset.
 # Stop the CPU and require a fully submitted two-page background before sampling.
 value={}
 for attempt in range(20):
  p.req('cpu.stepping')
  try:value=dict(actors=p.u32('sprite_draw_count'),batches=p.u32('stage_draw_count'),slices=p.u32('stage_slice_count'))
  finally:p.req('cpu.resume')
  if value['batches']>=1 and value['slices']>500:return value
  time.sleep(.02)
 return value
try:
 reset();arrange(40,x=220.);p.req('cpu.stepping')
 try:
  def wr(address,n):p.req('memory.write_u32',address=address,value=n)
  wr(p.symbols['game']+1696,4);wr(p.symbols['game']+1132,0x100);wr(p.symbols['sample_count'],0);wr(p.symbols['game']+824,10000)
  p.req('memory.write',address=p.symbols['level'],base64=base64.b64encode(struct.pack('<6ifIiI',1,4,1,0,0,0,2448.,1,2,0)).decode())
  for i in range(4):
   hp=240 if i==1 else 0
   p.req('memory.write',address=p.symbols['game']+36*(i+1),base64=base64.b64encode(struct.pack('<2f7i',150.+i*23.,82.+i*12.,hp,-1,0,0,0,0,0)).decode())
   wr(p.symbols['game']+592+i*56,7);wr(p.symbols['game']+576+i*56,7)
  p.req('memory.write',address=p.symbols['level']+40,base64=base64.b64encode(struct.pack('<7i',1,0,0,0,0,0,0)).decode())
  p.req('memory.write',address=p.symbols['level']+68,base64=base64.b64encode(b''.join(struct.pack('<2f2i',2448.+x,112.,int(i==2),1)for i,x in enumerate([90.,120.,150.]))).decode())
 finally:p.req('cpu.resume')
 before=p.u32('dropped_ticks');time.sleep(35);button('select',.04)
 import csv,statistics,shutil
 shutil.copy2(project/'build/lite-profile.csv',artifacts/'max-boss-battle-profile.csv')
 rows=list(csv.DictReader((artifacts/'max-boss-battle-profile.csv').read_text().splitlines()[1:]))[-30:]
 fps=[float(v['fps'])for v in rows]
 render_stats=render_snapshot()
 checks['boss_two_RAM_batches']=render_stats['actors']==2 and 1<=render_stats['batches']<=4
 checks['barbon_attacks_and_type']=struct.unpack('<i',p.read(p.symbols['level']+60,4))[0]>0 and struct.unpack('<i',p.read(p.symbols['game']+1696,4))[0]==4
 checks['food_remains_available']=all(struct.unpack('<i',p.read(p.symbols['level']+80+i*16,4))[0]==1 for i in range(3))
 checks['fps_target_met']=len(fps)==30 and min(fps)>=29 and statistics.median(fps)>=29.5
 checks['no_new_drops']=p.u32('dropped_ticks')==before
 checks['music_ok']=music()[0]==1 and music()[1]==0
 checks['level_remains_locked']=struct.unpack('<i',p.read(p.symbols['level']+8,4))[0]==1
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 checks['no_machine_dispatch_faults']=struct.unpack('<I',p.read(p.symbols['bk3_machine_stats']+12,4))[0]==0
 screenshot(artifacts/'max-boss-battle-profile.png')
 result=dict(checks=checks,render_snapshot=render_stats,seconds=35,last_30_fps=dict(min=min(fps),median=statistics.median(fps),max=max(fps)),eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Max selected, RAM character atlas, PPSSPP software-renderer stress fixture: final background position, active Barbon and three visible food sprites, player invulnerability to sustain combat. Not hardware performance.')
 (artifacts/'max-boss-performance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.close()

