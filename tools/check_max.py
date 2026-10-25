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
        if (status.get('game')or{}).get('id')!='SORL00026':
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

def st():
 v=struct.unpack('<6iIf2i',p.read(p.symbols['level']+188,40));return dict(zip(['cue','gate','wait','spawned','retired','overlap','spawn_mask','camera_step','stream','go_timer'],v))
def wl(off,fmt,*v):p.req('memory.write',address=p.symbols['level']+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
def retire(i):
 wr(36*(i+1)+8,0);p.req('memory.write',address=p.symbols['game']+800+52*(i+1),base64=base64.b64encode(bytes(52)).decode());wr(612+i*56,0)
def player_x(x):p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<f',x)).decode())
traces=[]
abi=list(struct.unpack('<5I',p.read(p.symbols['max_abi'],20)));maxoff=abi[1]
observations={}
source=json.loads((project/'assets/max-sor2-source.json').read_text())
def mx():return list(struct.unpack('<27i',p.read(p.symbols['game']+maxoff,108)))
def fixture(hp=100,target_x=82.,face=1,back=False):
 p.send(left=False,right=False,square=False,cross=False,triangle=False)
 reset();arrange(hp,x=target_x,one=True)
 p.req('cpu.stepping')
 try:
  p.req('memory.write_u32',address=p.symbols['player_character'],value=1)
  p.req('memory.write',address=p.symbols['game']+abi[3],base64=base64.b64encode(bytes(abi[0]-abi[3])).decode())
  p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f7i',100. if face<0 else 64.,100.,100,face,0,0,0,0,0)).decode())
  p.req('memory.write_u32',address=p.symbols['game']+824,value=10000)
  p.req('memory.write',address=p.symbols['game']+36,base64=base64.b64encode(struct.pack('<2f7i',target_x,100.,hp,face if back else -face,10000,10000,0,0,0)).decode())
 finally:p.req('cpu.resume')
 time.sleep(.06)
def wait_mode(mode,timeout=3):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  v=mx()
  if v[1]==mode:return v
  time.sleep(.01)
 raise AssertionError(('mode timeout',mode,mx(),state()))
def hold(back=False,face=1):
 fixture(200,94. if face<0 else 70.,face,back)
 button('left' if face<0 else 'right',.30)
 wait_mode(3)
def holdjump(back=False,face=1):
 hold(back,face);button('cross',.06);return wait_mode(6)
try:
 checks['mips_original_Max_and_upstream_FX_selftests']=p.u32('selftest_result')==0
 checks['ABI_legacy_offsets_preserved']=abi[:3]==[2096,1980,108]
 # Running uses real button edges and resolves the six original SoRR run poses.
 fixture(200,220.);p.send(right=True);time.sleep(.07);p.send(right=False);time.sleep(.07);p.send(right=True);time.sleep(.14)
 observations['run']=dict(mx=mx(),moves=moves(),frames=frames());checks['double_tap_run_animation']=mx()[2]==0x54 and moves()[0]==1 and frames()[0]in range(1100,1106)
 p.send(right=False);time.sleep(.10);checks['run_stops_on_release']=moves()[0]==0 and mx()[2]==0
 # Real button attacks, source collision damage and contact-driven combo advancement.
 fixture(200,82.);button('square',.06);time.sleep(.45)
 checks['original_first_combo_hit']=state()['enemies'][0][2]<200 and mx()[5]==1
 button('square',.06);time.sleep(.45)
 checks['original_second_combo_advances']=mx()[5]==2
 button('square',.06);time.sleep(.6)
 checks['third_combo_uses_native_sequence']=mx()[5]in(0,3)
 fixture(200,220.);button('square',.06);time.sleep(.4)
 checks['whiff_does_not_advance_combo']=mx()[5]==0
 # A single direction press never causes an automatic slide.
 fixture(200,220.);p.send(right=True);time.sleep(.04);p.send(square=True);time.sleep(.04)
 observations['single_direction']=wait_mode(1,.5);checks['single_direction_attack_not_blitz']=observations['single_direction'][2]==0x3a
 p.send(right=False,square=False);time.sleep(.6)
 # Native charged release threshold is 60 source ticks.
 fixture(200,220.);p.send(square=True);time.sleep(1.25);p.send(square=False);time.sleep(.04)
 observations['charged_release']=wait_mode(1,.5);checks['charged_release_selects_62']=observations['charged_release'][2]==0x62
 time.sleep(.6)
 fixture(200,220.);button('triangle',.06);time.sleep(.85)
 checks['neutral_whiff_costs_no_HP']=state()['player'][2]==100
 fixture(200,78.);button('triangle',.06);time.sleep(1.1)
 checks['neutral_contact_costs_8_HP']=state()['player'][2]==92 and state()['enemies'][0][2]<200
 fixture(200,220.);p.send(right=True);button('triangle',.06);p.send(right=False);time.sleep(1.0)
 checks['forward_special_whiff_costs_8_HP']=state()['player'][2]==92
 # Genuine held jumps keep orientation and side; no Axel vault.
 for face in [1,-1]:
  hold(False,face);before=state()['player'][3]
  button('cross',.06);v=wait_mode(6)
  checks['held_jump_keeps_facing_'+str(face)]=state()['player'][3]==before and struct.unpack('<i',p.read(p.symbols['game']+528,4))[0]==0
  button('square',.06);checks['front_ascent_starts_air_slam_'+str(face)]=mx()[1]==10
  time.sleep(1.4);checks['air_slam_releases_victim_'+str(face)]=moves()[16]==-1 and state()['enemies'][0][2]==160
 for face in [1,-1]:
  holdjump(True,face)
  button('square',.06);checks['back_ascent_B_ignored_'+str(face)]=mx()[1]==6
  end=time.monotonic()+1.5
  while mx()[11]<0 and time.monotonic()<end:time.sleep(.006)
  button('square',.06);v=mx();checks['back_descent_atomic_'+str(face)]=v[1]in(11,12)
  time.sleep(1.3);checks['atomic_70_HP_and_release_'+str(face)]=state()['enemies'][0][2]==130 and moves()[16]==-1
 holdjump(False);end=time.monotonic()+1.5
 while mx()[11]<0 and time.monotonic()<end:time.sleep(.006)
 button('square',.06);checks['front_descent_B_ignored']=mx()[1]==6
 time.sleep(1.0);checks['held_jump_without_throw_no_damage_or_knockdown']=state()['enemies'][0][2]==200 and struct.unpack('<i',p.read(p.symbols['game']+852,4))[0]==0 and moves()[16]==-1
 # Ground throws keep their distinct original pending damage, then one floor hit.
 for back in [False,True]:
  hold(back);p.send(left=not back);button('square',.06);p.send(left=False);time.sleep(1.4)
  checks['ground_throw_damage_'+str(back)]=state()['enemies'][0][2]==200-(62 if back else 34) and moves()[16]==-1
 checks['native_sprites_resolved']=p.u32('missing_sprite_frames')==0
 checks['no_dispatch_faults']=struct.unpack('<I',p.read(p.symbols['bk3_machine_stats']+12,4))[0]==0
 screenshot(artifacts/'max-combat.png')
 result=dict(checks=checks,observations=observations,abi=abi,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real PSP input and debugger-arranged isolated targets; original collision/timing extraction is independently checked by check_max_assets.py. Hardware not tested.')
 (artifacts/'max-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(left=False,right=False,square=False,cross=False,triangle=False);p.close()
