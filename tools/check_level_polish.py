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
def lv():
 v=struct.unpack('<6ifIiI',p.read(p.symbols['level'],40));return dict(zip(['enabled','wave','locked','go','finished','timer','camera','generation','slots','clears'],v))
def wr(off,n):p.req('memory.write_u32',address=p.symbols['game']+off,value=n&0xffffffff)
def native_reset():
 p.send(ltrigger=True,rtrigger=True);time.sleep(.12);p.send(ltrigger=False,rtrigger=False);time.sleep(.12)
def kill_wave():
 p.req('cpu.stepping')
 try:
  for i in range(4):
   wr(36*(i+1)+8,0);p.req('memory.write',address=p.symbols['game']+800+52*(i+1),base64=base64.b64encode(bytes(52)).decode());wr(612+i*56,0)
  wr(8,80);wr(824,10000)
 finally:p.req('cpu.resume')
 time.sleep(.15)
def walk_to_wave(w):
 p.send(right=True);deadline=time.monotonic()+18
 while lv()['wave']<w and time.monotonic()<deadline:time.sleep(.08)
 p.send(right=False);time.sleep(.10)
 if lv()['wave']!=w:raise RuntimeError('Did not reach wave '+str(w)+': '+str(lv()))
def wait_entry():
 deadline=time.monotonic()+8
 while struct.unpack('<I',p.read(p.symbols['level']+132,4))[0] and time.monotonic()<deadline:time.sleep(.05)
 return struct.unpack('<I',p.read(p.symbols['level']+132,4))[0]==0

def ext():return struct.unpack('<I4f9i',p.read(p.symbols['level']+132,56))
def poke_l(off,fmt,*v):p.req('memory.write',address=p.symbols['level']+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
try:
 native_reset();v=ext();checks['selftest']=p.u32('selftest_result')==0
 checks['offscreen_staggered_start']=v[0]==3 and all(e[0]>240 for e in state()['enemies'][:2]) and v[5]<v[6]
 checks['intro_banner_active']=v[9]>0 and v[11]>0
 black=False
 for attempt in range(10):
  p.req('cpu.stepping')
  try:
   raw=p.read(p.u32('presented_buffer'),512*272*2);black=raw[96*1024:96*1024+960]==bytes(960)
  finally:p.req('cpu.resume')
  if black:break
  time.sleep(.01)
 checks['intro_draws_black_blinds']=black
 screenshot(artifacts/'level-intro.png')
 button('start',.04);v=ext();time.sleep(.12);checks['pause_freezes_entry_and_fade']=ext()==v
 button('start',.04);wr(824,10000);seen=set();walking=False;invulnerable=True;deadline=time.monotonic()+7
 while ext()[0] and time.monotonic()<deadline:
  mask=ext()[0];seen.add(mask);es=state()['enemies'];fs=frames()
  for i in range(4):
   if mask&(1<<i):
    invulnerable &= struct.unpack('<i',p.read(p.symbols['game']+824+52*(i+1),4))[0]>0
    if 0<es[i][0]<240:walking |= fs[i+1] not in [1,7,9]
  time.sleep(.05)
 checks['entrances_finish']=ext()[0]==0
 checks['entrance_mask_changes']=len(seen)>=2
 checks['walking_animation_visible']=walking
 checks['entrance_invulnerability']=invulnerable
 deadline=time.monotonic()+3
 while ext()[11]>0 and time.monotonic()<deadline:time.sleep(.04)
 checks['intro_and_banner_finish']=ext()[9]==0 and ext()[11]==0
 screenshot(artifacts/'entries-finished.png')
 # Reach the boss through the production last-wave-clear path, retaining its own entrance.
 native_reset();time.sleep(.85);p.req('cpu.stepping');poke_l(188,'<2i',20,1);poke_l(200,'<i',20);poke_l(4,'<i',4);poke_l(24,'<f',2448.);p.req('cpu.resume');kill_wave()
 v=ext();checks['boss_entrance_is_solo']=v[0]==2 and lv()['slots']==2 and state()['enemies'][1][0]>240 and struct.unpack('<i',p.read(p.symbols['level']+40,4))[0]==1
 checks['boss_warning_banner']=v[11]>0
 screenshot(artifacts/'boss-warning.png');checks['boss_entrance_finishes']=wait_entry()
 kill_wave();checks['boss_clear_GO']=lv()['go']==1 and lv()['locked']==0
 arrow=[]
 for timer in [0,6]:
  found=-1
  for attempt in range(12):
   poke_l(20,'<i',timer);time.sleep(.04);p.req('cpu.stepping')
   try:
    raw=p.read(p.u32('presented_buffer'),512*272*2)
    yellow=[x for y in range(76,106)for x in range(410,470)if struct.unpack_from('<H',raw,y*1024+x*2)[0]==0x271f]
    found=min(yellow)if yellow else -1
   finally:p.req('cpu.resume')
   if found>0:break
  arrow.append(found)
 checks['GO_arrow_moves_sideways']=min(arrow)>0 and arrow[0]!=arrow[1]
 screenshot(artifacts/'GO-bob.png')
 p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<f',220.)).decode());time.sleep(.12)
 checks['exit_waits_for_fade']=ext()[10]>0 and lv()['finished']==0 and state()['won']==0
 p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<f',100.)).decode());time.sleep(.45)
 checks['outro_still_pending']=lv()['finished']==0
 screenshot(artifacts/'level-outro.png');time.sleep(1.2)
 checks['outro_cannot_be_cancelled']=lv()['finished']==1 and state()['won']==1 and struct.unpack('<i',p.read(p.symbols['flow'],4))[0]==5
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,entrance_masks=sorted(seen),arrow_positions=arrow,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real entry/pose/GUI/fade timers and framebuffer. HP fixtures accelerate the final-wave/boss clear; no claim of hardware performance.')
 (artifacts/'level-polish-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(right=False,left=False,start=False,square=False);p.close()
