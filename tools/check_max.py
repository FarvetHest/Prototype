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
        if (status.get('game')or{}).get('id')!='SORL00023':
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
checks={};seen={};rendered={}
m=json.loads((project/'assets/max-manifest.json').read_text());aliases={int(k):v for k,v in m['aliases'].items()};poses={f['id']:f for f in m['frames']}
def write_sym(name,n):p.req('memory.write_u32',address=p.symbols[name],value=n&0xffffffff)
def quiet(x=220,hp=100):reset();arrange(hp,x=x,one=True);wr(824,10000)
def observe(seconds):
 ids=set();deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:ids.add(frames()[0]);time.sleep(.008)
 return ids
try:
 checks['native_selftest']=p.u32('selftest_result')==0
 checks['default_is_Axel']=p.u32('player_character')==0
 button('right',.04);checks['title_selects_Max']=p.u32('player_character')==1
 button('left',.04);checks['title_returns_to_Axel']=p.u32('player_character')==0
 button('right',.04);screenshot(artifacts/'max-title.png');button('start',.04);time.sleep(.9)
 checks['Max_starts_in_family6']=p.u32('actor_family')==6 and frames()[0]in [1,2,3]
 quiet();before=state()['player'][0];t=p.u32('logic_count');p.send(right=True);time.sleep(.30);p.send(right=False);elapsed=p.u32('logic_count')-t;distance=state()['player'][0]-before
 checks['Max_slower_walk']=6<=elapsed<=12 and abs(distance-elapsed)<2
 checks['walking_original_frames']=bool(observe(.2))
 quiet(x=82);p.send(square=True);time.sleep(.035);p.send(square=False);seen['jab']=sorted(observe(.4));checks['heavy_jab_damage3']=state()['enemies'][0][2]==97
 checks['jab_uses_Max10']=10 in seen['jab']
 quiet();p.send(square=True);time.sleep(.78);p.send(square=False);seen['charged']=sorted(observe(.5));checks['held_release_Max_combo']=bool(set(seen['charged'])&{24,25,26,27})
 quiet();p.send(cross=True);time.sleep(.04);p.send(cross=False);seen['jump']=sorted(observe(1.0));checks['jump_original_poses']=bool(set(seen['jump'])&{11,12,13}) and state()['player'][7]==0
 quiet();p.send(triangle=True);time.sleep(.04);p.send(triangle=False);seen['special']=sorted(observe(.7));checks['neutral_special_Max_spin']=len(set(seen['special'])&{24,25,26,27,28})>=3
 checks['full_charge_special_no_HP_cost']=state()['player'][2]==100
 quiet();wr(552,16);p.send(triangle=True);time.sleep(.04);p.send(triangle=False);time.sleep(.8);checks['partial_charge_special_pays_HP']=state()['player'][2]==88
 quiet();p.send(right=True,triangle=True);time.sleep(.04);p.send(right=False,triangle=False);seen['forward']=sorted(observe(.8));checks['forward_special_Max_poses']=len(set(seen['forward'])&{35,36,37,38})>=2
 # Actual grab/throw input; fixture seeds only the hold and freezes the victim AI.
 quiet(x=120);p.req('cpu.stepping')
 for off,n in [(512,1),(524,0),(528,0),(256,0),(576,0),(580,10000),(1088,160),(1120,1),(1136,144),(1164,0),(1324,12)]:wr(off,n)
 p.req('cpu.resume');p.send(left=True,square=True);time.sleep(.035);p.send(left=False,square=False);seen['throw']=sorted(observe(1.4));checks['throw_uses_Max_poses']=len(set(seen['throw'])&{153,154,155,156})>=2
 checks['heavy_throw_lands']=state()['enemies'][0][2]<100 and moves()[16]==-1
 quiet();p.req('cpu.stepping');wr(8,50);p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f',120.,112.)).decode());wl(0,'<6ifIiI',1,1,0,1,0,0,260.,2,0,1);wl(68,'<2f2i',380.,112.,0,1);wl(132,'<96s',bytes(96));p.req('cpu.resume');p.send(square=True);pickup_frames=observe(.10);p.send(square=False);time.sleep(.25)
 checks['Max_pickup_pose74']=74 in pickup_frames
 checks['Max_food_heals25']=state()['player'][2]==75
 quiet();checks['new_run_preserves_Max']=p.u32('player_character')==1
 # Pixel and pivot proof for every shipped pose in both orientations at 1:1.
 # Native scale is exercised by dedicated default-view performance tests.
 write_sym('stage_native_view',0);wr(184,1);p.req('cpu.stepping');p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f',64.,126.)).decode());write_sym('actor_lift',0);p.req('cpu.resume')
 raw=(project/'assets/max.t8').read_bytes();linear=bytearray(len(raw));o=0
 for by in range(0,m['atlas_pages']*512,8):
  for bx in range(0,512,16):
   for dy in range(8):linear[(by+dy)*512+bx:(by+dy)*512+bx+16]=raw[o:o+16];o+=16
 for facing in [1,-1]:
  wr(12,facing);count=0;pixels=0
  for f in m['frames']:
   write_sym('actor_frames',f['id']);time.sleep(.08);p.req('cpu.stepping')
   try:
    frame=p.read(p.u32('presented_buffer'),512*272*2);matched=total=0
    for y in range(f['h']):
     for x in range(f['w']):
      idx=linear[(f['v']+y)*512+f['u']+x]
      if not idx:continue
      sx=128-f['px']+x if facing==1 else 128+f['px']-1-x;sy=258-f['py']+y
      if not(0<=sx<480 and 145<=sy<272):continue
      r,g,b,a=m['palette'][idx];want=(r>>3)|((g>>2)<<5)|((b>>3)<<11);matched+=struct.unpack_from('<H',frame,sy*1024+sx*2)[0]==want;total+=1
    if matched!=total:rendered[str(f['id'])+'_'+str(facing)]=dict(matched=matched,total=total)
    count+=matched==total;pixels+=total
   finally:p.req('cpu.resume')
  checks['all_58_poses_pixels_facing_'+str(facing)]=count==58 and pixels>50000
  rendered['summary_'+str(facing)]=dict(poses=count,pixels=pixels)
 write_sym('stage_native_view',1);checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 checks['no_dispatch_faults']=struct.unpack('<I',p.read(p.symbols['bk3_machine_stats']+12,4))[0]==0
 # Continue and switching back must retain/select the matching mechanics profile.
 quiet();p.req('cpu.stepping');wr(8,0);wr(800,0);p.req('memory.write_u32',address=p.symbols['flow']+4,value=1);p.req('cpu.resume');time.sleep(.15);button('start',.04)
 checks['continue_keeps_Max']=p.u32('player_character')==1 and p.u32('actor_family')==6 and state()['player'][2]==100
 p.req('memory.write_u32',address=p.symbols['flow'],value=0);button('left',.04);button('start',.04);quiet(x=82);p.send(square=True);time.sleep(.035);p.send(square=False);time.sleep(.4)
 checks['switch_back_restores_Axel_damage2']=p.u32('player_character')==0 and p.u32('actor_family')==0 and state()['enemies'][0][2]==98
 result=dict(checks=checks,observed=seen,rendered=rendered,walk=dict(ticks=elapsed,distance=distance),eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real selection/controller, Max heavy-profile moves and original-pixel proof at 1:1 for all58 poses/mirrors. Fixtures position targets or seed a grab; Max remains a BK3/Lite mechanics adapter, not original SoR2 code execution.')
 (artifacts/'max-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(right=False,left=False,start=False,cross=False,square=False,triangle=False);p.close()
