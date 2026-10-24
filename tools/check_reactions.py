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

def wl(off,fmt,*values):p.req('memory.write',address=p.symbols['level']+off,base64=base64.b64encode(struct.pack(fmt,*values)).decode())
def food():return [list(struct.unpack('<2f2i',p.read(p.symbols['level']+68+i*16,16)))for i in range(3)]
def boss():return list(struct.unpack('<7i',p.read(p.symbols['level']+40,28)))
def food_pixels(id):
 m=json.loads((project/'assets/hud-manifest.json').read_text());f=next(v for v in m['frames'] if v['file']=='item' and v['id']==id);atlas=(project/'assets/hud.rgba').read_bytes()
 raw=p.read(p.u32('presented_buffer'),512*272*2);matched=total=0
 for y in range(f['h']):
  for x in range(f['w']):
   u=f['u']+x;v=f['v']+y;byte=u*4;off=((v//8)*64+byte//16)*128+(v%8)*16+byte%16;r,g,b,a=atlas[off:off+4]
   if not a:continue
   want=(r>>3)|((g>>2)<<5)|((b>>3)<<11);screen=(247-f['h']+y)*1024+(240-f['w']//2+x)*2
   matched+=struct.unpack_from('<H',raw,screen)[0]==want;total+=1
 return dict(matched=matched,total=total)
def fixture(isboss=False,hp=50):
 native_reset();p.req('cpu.stepping')
 try:
  for i in range(4):wr(36*(i+1)+8,0)
  wr(8,hp);wr(824,10000)
  p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f',120.,112.)).decode())
  wl(0,'<6ifIiI',1,1,0,1,0,0,260.,2,0,1)
  wl(40,'<7i',0,0,0,0,0,0,0);wl(68,'<2f2i',380.,112.,0,1);wl(116,'<4I',1,0,0,0);wl(132,'<96s',bytes(96))
 finally:p.req('cpu.resume')
 time.sleep(.12)

source=json.loads((project/'assets/enemy-variety.json').read_text())['types']
manifest=json.loads((project/'assets/manifest.json').read_text())
native=json.loads((project/'assets/enemy-native.json').read_text())
samples=[]
def put(off,fmt,*v):p.req('memory.write',address=p.symbols['game']+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
def extra(i=0):return list(struct.unpack('<8i',p.read(p.symbols['game']+1664+i*32,32)))
def setup(t,x=150.,y=100.,action=0,ai=6):
 reset();arrange(40,x=x,one=True);p.req('cpu.stepping')
 try:
  for i in range(1,4):wr(36*(i+1)+8,0)
  put(0,'<2f7i',64.,100.,100,1,0,0,0,0,0)
  put(36,'<2f7i',x,y,40,-1,0,0,0,0,0)
  put(1664,'<8i',t,action,0,0,0,0,0,0)
  put(576,'<5i',7,0,12,0,ai)
  put(1324,'<10i',0x48 if action else 2,0,-1,0,0,0,0,0,0,0)
  put(1512,'<i',-1)
  put(1568,'<6i',0,0,0,0,0,0)
  wr(1084+48,28 if t==2 else 30);wr(824,0)
 finally:p.req('cpu.resume')
def pose_pixels(t,fid):
 f=next(f for f in manifest['frames']if f['family']==t+1 and f['id']==fid)
 # Snapshot is paused; actual framebuffer uses native source pixels at the source pivot.
 raw=p.read(p.u32('presented_buffer'),512*272*2);a=state()['enemies'][0];x=int(a[0]*2);foot=220+int((a[1]-76)*.76);frame=native['electra'if t==2 else'zack']['frames'][str(fid)];pix=bytes.fromhex(frame['pixels']);palette=native['electra'if t==2 else'zack']['palette'];matched=total=0
 for yy in range(f['h']):
  for xx in range(f['w']):
   idx=pix[(yy+f['crop_top'])*frame['w']+xx+f['crop_left']]
   if not idx:continue
   sx=x-f['px']+xx;sy=foot-f['py']+yy
   if not(0<=sx<480 and 60<=sy<272):continue
   r,g,b,alpha=palette[idx];want=(r>>3)|((g>>2)<<5)|((b>>3)<<11)
   matched+=struct.unpack_from('<H',raw,sy*1024+sx*2)[0]==want;total+=1
 return dict(matched=matched,total=total,page=f['y']//512)

def rx():return list(struct.unpack('<12i',p.read(p.symbols['game']+1792,48)))
def capture(back=False):
 setup(3,x=150.);p.req('cpu.stepping');put(36,'<2f',70.,100.);wr(12,-1 if back else 1);put(576,'<2i',7,0);p.req('cpu.resume');time.sleep(.08)
trace={}
try:
 checks['selftest']=p.u32('selftest_result')==0
 capture();checks['front_capture']=rx()[0]==0 and rx()[1]==0 and frames()[0]==922
 checks['capture_preserves_player_position']=abs(state()['player'][0]-64)<.01 and abs(state()['player'][1]-100)<.01
 screenshot(artifacts/'zack-front-capture.png');button('start',.04);before=rx();time.sleep(.15);checks['pause_freezes_hold']=rx()==before;button('start',.04)
 deadline=time.monotonic()+1.7
 while state()['player'][2]==100 and time.monotonic()<deadline:time.sleep(.015)
 checks['captured_knees_deal_damage']=state()['player'][2]<100
 capture();button('triangle',.04);checks['special_escapes_capture']=rx()[0]==-1 and struct.unpack('<i',p.read(p.symbols['game']+512,4))[0]==8
 capture();p.req('cpu.stepping');wr(36+8,0);p.req('cpu.resume');time.sleep(.08);checks['holder_death_releases_player']=rx()[0]==-1 and not(struct.unpack('<i',p.read(p.symbols['game']+1088,4))[0]&16)
 capture(True);checks['back_capture']=rx()[0]==0 and rx()[1]==1 and frames()[0]==923
 button('cross',.04);checks['back_jump_escape']=rx()[0]==-1 and struct.unpack('<i',p.read(p.symbols['game']+512,4))[0]==7
 capture(True);time.sleep(1.15);checks['back_hold_expires']=rx()[0]==-1
 # Front block uses real Square damage resolution; rear hit must bypass it.
 for rear in [False,True]:
  setup(3,x=82.,action=14);p.req('cpu.stepping');wr(48,1 if rear else -1);put(1664+28,'<i',30);p.req('cpu.resume');button('square',.04);time.sleep(.15)
  checks['rear_bypasses_block'if rear else'front_blocks_without_HP_loss']=state()['enemies'][0][2]<40 if rear else state()['enemies'][0][2]==40 and rx()[9]>0
  screenshot(artifacts/('zack-rear-hit.png'if rear else'zack-block.png'))
 # Third blocked strike + a pinned RNG seed selects the declared counter policy.
 setup(3,x=82.,action=14,ai=10);p.req('cpu.stepping');wr(1664+16,2);wr(1664+28,30);wr(568,1);p.req('cpu.resume');button('square',.04);time.sleep(.1)
 checks['blocked_combo_counter']=rx()[10]>0
 deadline=time.monotonic()+.8
 while state()['player'][2]==100 and time.monotonic()<deadline:time.sleep(.015)
 checks['counter_deals_original_damage']=state()['player'][2]==96 and struct.unpack('<i',p.read(p.symbols['game']+1528,4))[0]==132
 screenshot(artifacts/'zack-counter.png')
 # Long electrified whip. Source scripts and collision geometry are still real MIPS.
 setup(2,x=150.);p.req('cpu.stepping');put(0,'<2f',106.5,100.);put(1664,'<8i',2,11,0,0,0,0,0,0);wr(1324,0x4a);p.req('cpu.resume')
 deadline=time.monotonic()+2;seen=set();started=False
 while time.monotonic()<deadline:
  r=rx()
  if r[5]:
   seen.add(frames()[0]);started=True
   if len(seen)==1 and not trace:
    screenshot(artifacts/'electra-electric-reaction.png');button('start',.04);before=rx();time.sleep(.12);checks['pause_freezes_electric_reaction']=rx()==before;button('start',.04);trace['paused']=before
  elif started:break
  time.sleep(.012)
 checks['electric_damage_5']=state()['player'][2]==95
 checks['both_native_electric_poses']={920,921}<=seen
 checks['electric_state_ends_at_landing']=started and rx()[5]==0
 trace['electric_frames']=sorted(seen)
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,trace=trace,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Debugger arranges type, position, guard and RNG; actual capture AI, Square/triangle/Cross, MIPS damage, held poses, shock, physics and pause run normally. Block/counter are explicitly adapted from Obj_Blondie for Zack.')
 (artifacts/'reaction-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(left=False,right=False,start=False,square=False,triangle=False,cross=False);p.close()
