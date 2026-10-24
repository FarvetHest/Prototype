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
        if (status.get('game')or{}).get('id')!='SORL00022':
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
# Legacy 1:1 projection isolates original-pixel asset checks; native projection is
# covered by check_route1 and the default performance runs.
p.req('memory.write_u32',address=p.symbols['stage_native_view'],value=0)
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
 p.req('cpu.stepping')
 try:raw=p.read(p.u32('presented_buffer'),512*272*2)
 finally:p.req('cpu.resume')
 matched=total=0
 for y in range(f['h']):
  for x in range(f['w']):
   u=f['u']+x;v=f['v']+y;byte=u*4;off=((v//8)*64+byte//16)*128+(v%8)*16+byte%16;r,g,b,a=atlas[off:off+4]
   if not a:continue
   want=(r>>3)|((g>>2)<<5)|((b>>3)<<11);screen=(247-f['h']+y)*1024+(120-f['w']//2+x)*2
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
try:
 checks['selftest']=p.u32('selftest_result')==0
 fixture();checks['touch_does_not_pick']=state()['player'][2]==50 and food()[0][3]==1
 p.send(square=True,right=True);pickup_seen=False;pickup_deadline=time.monotonic()+.15
 while time.monotonic()<pickup_deadline:
  if frames()[0]==910 and state()['player'][6]==0 and struct.unpack('<i',p.read(p.symbols['level']+180,4))[0]>0:
   pickup_seen=True;break
  time.sleep(.005)
 p.send(square=False,right=False)
 checks['square_starts_pickup_pose']=pickup_seen
 checks['pickup_locks_walk']=abs(state()['player'][0]-120)<.01
 screenshot(artifacts/'pickup-animation.png');time.sleep(.25)
 checks['apple_heals_25']=state()['player'][2]==75 and food()[0][3]==0 and p.u32('ui_player_hp')==75
 checks['pickup_returns_idle']=frames()[0]!=910 and state()['player'][6]==0
 time.sleep(.2);checks['food_consumed_once']=state()['player'][2]==75
 fixture(hp=90);button('square',.04);time.sleep(.15);checks['apple_caps_100']=state()['player'][2]==100
 fixture(hp=100);button('square',.04);time.sleep(.2);checks['full_HP_keeps_food']=food()[0][3]==1 and struct.unpack('<i',p.read(p.symbols['level']+180,4))[0]==0
 # Move the asset probe left of the native foreground lamp; combat pickup fixtures above stay unchanged.
 wl(68,'<f',320.);p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<f',92.)).decode());time.sleep(.1);screenshot(artifacts/'food-apple.png');apple_pixels=food_pixels(4);checks['rendered_apple_matches_source']=apple_pixels['matched']==apple_pixels['total']
 fixture();p.send(square=True);time.sleep(.04);p.send(square=False);p.send(start=True);time.sleep(.04);p.send(start=False);before=struct.unpack('<i',p.read(p.symbols['level']+180,4))[0];hp=state()['player'][2];time.sleep(.15)
 checks['pause_freezes_pickup']=before>0 and struct.unpack('<i',p.read(p.symbols['level']+180,4))[0]==before and state()['player'][2]==hp
 button('start',.04);time.sleep(.2);checks['resume_finishes_pickup']=state()['player'][2]==75 and food()[0][3]==0
 fixture(hp=100);button('cross',.04);wr(8,40);p.send(square=True);time.sleep(.06);p.send(square=False)
 checks['airborne_attack_cannot_pick']=state()['player'][7]>0 and state()['player'][2]==40 and food()[0][3]==1
 time.sleep(1.3);checks['landing_alone_does_not_pick']=state()['player'][2]==40 and food()[0][3]==1
 button('square',.04);time.sleep(.2);checks['new_square_after_landing_picks']=state()['player'][2]==65 and food()[0][3]==0
 fixture(hp=100);p.req('cpu.stepping');wl(68,'<2f2i',380.,112.,1,1);wr(8,30);p.req('cpu.resume');button('square',.04);time.sleep(.2)
 checks['chicken_heals_60']=state()['player'][2]==90 and food()[0][3]==0
 fixture(hp=100);p.req('cpu.stepping');wl(68,'<2f2i',320.,112.,1,1);p.req('cpu.resume');p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<f',92.)).decode());time.sleep(.1);screenshot(artifacts/'food-chicken.png');chicken_pixels=food_pixels(18);checks['rendered_chicken_matches_source']=chicken_pixels['matched']==chicken_pixels['total']
 fixture();p.send(square=True);time.sleep(.8);p.send(square=False);time.sleep(.12)
 checks['pickup_hold_release_has_no_charged_kick']=state()['player'][2]==75 and state()['player'][6]==0 and frames()[0]!=910 and struct.unpack('<2i',p.read(p.symbols['held_attack'],8))==(0,0)
 fixture();p.send(rtrigger=True);button('square',.04);p.send(rtrigger=False);time.sleep(.15);checks['rear_attack_does_not_pick']=state()['player'][2]==50 and food()[0][3]==1
 fixture();p.send(square=True);time.sleep(.04);p.send(square=False);wr(20,10);time.sleep(.3);checks['hurt_cancels_before_commit']=state()['player'][2]==50 and food()[0][3]==1 and struct.unpack('<i',p.read(p.symbols['level']+180,4))[0]==0
 fixture();button('square',.04);time.sleep(.2);mask=struct.unpack('<I',p.read(p.symbols['level']+120,4))[0]
 p.req('cpu.stepping');wr(8,0);wr(800,0);p.req('memory.write_u32',address=p.symbols['flow']+4,value=1);p.req('cpu.resume');time.sleep(.15);button('start',.04)
 checks['continue_does_not_respawn_food']=struct.unpack('<I',p.read(p.symbols['level']+120,4))[0]==mask and food()[0][3]==0
 native_reset();checks['new_game_clears_food']=struct.unpack('<2I',p.read(p.symbols['level']+116,8))==(0,0) and not any(f[3]for f in food())
 # Actual boss AI, source animation and collision paths; memory fixtures only position the fight.
 reset();arrange(100,x=220.);p.req('cpu.stepping')
 try:
  for i in range(4):wr(36*(i+1)+8,0)
  p.req('memory.write',address=p.symbols['game']+72,base64=base64.b64encode(struct.pack('<2f7i',140.,100.,240,-1,0,0,0,0,0)).decode())
  p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f7i',64.,100.,100,1,0,0,0,0,0)).decode())
  for i in range(5):wr(1492+i*4,0)
  wl(0,'<6ifIiI',1,4,1,0,0,0,2448.,6,2,5);wl(40,'<7i',1,0,0,0,0,0,0)
 finally:p.req('cpu.resume')
 phases=set();modes=set();deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  b=boss();phases.add(b[1]);modes.add(struct.unpack('<i',p.read(p.symbols['game']+1364,4))[0]);time.sleep(.035)
 checks['boss_telegraph_dash_recover']=set([0,1,2,3])<=phases and boss()[6]>0
 checks['boss_kick_animation']=0x30 in modes
 checks['boss_attacks_damage_player']=state()['player'][2]<100
 checks['boss_cannot_clear_while_alive']=lv()['locked']==1 and state()['won']==0
 screenshot(artifacts/'boss-fight.png')
 # Interrupted windup: real player jab through normal hit boxes.
 p.req('cpu.stepping')
 try:
  wr(824,10000);wr(8,100);wr(80,240);wr(92,0);wr(576+56,7);wr(1364,2);wr(1492+8,10000)
  p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f7i',64.,100.,100,1,0,0,0,0,0)).decode())
  p.req('memory.write',address=p.symbols['game']+72,base64=base64.b64encode(struct.pack('<2f',82.,100.)).decode())
  p.req('memory.write',address=p.symbols['game']+904,base64=base64.b64encode(bytes(52)).decode())
  wl(44,'<2i',1,24)
 finally:p.req('cpu.resume')
 button('square',.04);time.sleep(.12)
 checks['boss_takes_normal_damage']=state()['enemies'][1][2]<240
 checks['boss_windup_interruptible']=boss()[1]==3
 reset();arrange(240,x=70.,one=True);p.req('cpu.stepping')
 for i in [0,2,3]:wr(36*(i+1)+8,0)
 # Move the unarmed Donovan slot to the source grab fixture and freeze its AI.
 p.req('memory.write',address=p.symbols['game']+72,base64=base64.b64encode(struct.pack('<2f7i',70.,100.,240,-1,0,0,0,0,0)).decode())
 p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f',64.,100.)).decode())
 wr(1500,10000);wl(0,'<6ifIiI',1,4,1,0,0,0,2448.,6,2,5);wl(40,'<7i',1,0,0,0,0,0,0);p.req('cpu.resume')
 p.send(right=True);time.sleep(.12);p.send(right=False);time.sleep(.04)
 checks['boss_can_be_grabbed']=moves()[16]==1
 p.send(left=True);button('square',.04);p.send(left=False);checks['boss_throw_started']=struct.unpack('<i',p.read(p.symbols['game']+512,4))[0]==5;time.sleep(2.)
 checks['boss_throw_lands_with_damage']=state()['enemies'][1][2]<240 and moves()[16]==-1
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,apple_pixels=apple_pixels,chicken_pixels=chicken_pixels,phases=sorted(phases),attack_modes=sorted(modes),eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real pickup, jump and attack input; debugger fixtures position actors/food and force continue. Native selftests separately cover boss rage, anti-air and death gating.')
 (artifacts/'food-boss-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(right=False,left=False,start=False,cross=False,square=False);p.close()
