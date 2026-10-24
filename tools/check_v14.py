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
def bk():return list(struct.unpack('<29i',p.read(p.symbols['game']+396,116)))
def wr(off,v):p.req('memory.write_u32',address=p.symbols['game']+off,value=v&0xffffffff)
def held():return list(struct.unpack('<2i',p.read(p.symbols['held_attack'],8)))
def fixture():reset();arrange(100,x=220.)
traces={}
enemy_frames_ref=json.loads((project/'assets/enemy-rom-match.json').read_text())
try:
 checks['selftest']=p.u32('selftest_result')==0
 fixture();p.send(square=True);time.sleep(.75)
 checks['hold_arms_without_auto_repeat']=held()[0]>=40 and held()[1]==1 and bk()[4]==0
 p.send(square=False);time.sleep(.05);checks['release_starts_kick']=bk()[1]==11 and bk()[4]==1
 time.sleep(.10);screenshot(artifacts/'charged-kick.png');time.sleep(.55)
 checks['release_fires_once']=bk()[4]==0 and held()==[0,0]
 fixture();button('square',.08);time.sleep(.2);checks['short_tap_no_charged_kick']=bk()[1]!=11 and bk()[4]==0
 fixture();p.send(square=True);time.sleep(.75);button('start',.04);p.send(square=False);button('start',.04);time.sleep(.1)
 checks['pause_discards_charge']=held()==[0,0] and bk()[1]!=11
 fixture();p.send(square=True);time.sleep(.75);p.req('cpu.stepping');wr(20,20);p.req('cpu.resume');time.sleep(.08);p.send(square=False);time.sleep(.1)
 checks['hit_discards_charge']=held()==[0,0] and bk()[1]!=11
 fixture();p.send(square=True);time.sleep(.75);p.req('cpu.stepping')
 p.req('memory.write',address=p.symbols['game']+36,base64=base64.b64encode(struct.pack('<2f',82.,100.)).decode());p.req('cpu.resume')
 p.send(square=False);time.sleep(.65);checks['charged_kick_damages_and_knocks_down']=state()['enemies'][0][2]<=94 and struct.unpack('<i',p.read(p.symbols['game']+852,4))[0]!=0
 for dx,key in [(1,'right'),(-1,'left')]:
  fixture();p.send(**{key:True,'cross':True});time.sleep(.16);p.send(cross=False)
  checks[key+'_directional_jump_is_not_auto_attack']=frames()[0] in (12,13) and bk()[1]==3 and state()['player'][7]==1 and state()['player'][6]==0
  screenshot(artifacts/('jump-'+key+'.png'));p.send(square=True);time.sleep(.05);p.send(square=False)
  checks[key+'_flying_kick']=bk()[1]==9 and frames()[0] in (22,23)
  p.send(**{key:False});time.sleep(.7);checks[key+'_jump_lands']=state()['player'][7]==0
 fixture();p.send(cross=True,square=True,right=True);time.sleep(.16);p.send(cross=False,square=False,right=False)
 checks['simultaneous_direction_jump_attack_is_flying']=bk()[1]==9
 fixture();p.send(cross=True);time.sleep(.15);p.send(cross=False);p.send(square=True);time.sleep(.05);p.send(square=False)
 checks['neutral_jump_keeps_vertical_attack']=bk()[1]==8
 reset();arrange(100,x=74.,one=True);p.send(cross=True);time.sleep(.08);p.send(cross=False);p.send(down=True,square=True);time.sleep(.10);p.send(down=False,square=False)
 checks['down_attack_stuns_without_throwing']=state()['enemies'][0][2]==96 and struct.unpack('<i',p.read(p.symbols['game']+852,4))[0]==1
 screenshot(artifacts/'tucked-contact.png')
 # Both enemy families: source attachment must keep the victim's own X/Y origin.
 for enemy in [0,1]:
  for back in [False,True]:
   reset();arrange(100,x=120.,one=True);p.req('cpu.stepping')
   actor=36*(enemy+1);body=800+52*(enemy+1)
   p.req('memory.write',address=p.symbols['game']+actor,base64=base64.b64encode(struct.pack('<2f7i',120.,100.,100,-1,10000,0,0,0,0)).decode())
   for off,v in [(512,1),(524,enemy),(528,int(back)),(256,enemy),(1088,160),(1120,enemy+1),(1084+48*(enemy+1)+4,144),(1084+48*(enemy+1)+32,0),(1324+40*enemy,14 if back else 12),(512+64+56*enemy,0),(512+68+56*enemy,10000)]:wr(off,v)
   p.req('cpu.resume');time.sleep(.06);p.send(**({'square':True} if back else {'left':True,'square':True}));time.sleep(.06);p.send(square=False,left=False)
   name=('back' if back else 'front')+str(enemy);a=state();checks[name+'_no_origin_snap']=abs(a['enemies'][enemy][0]-(120 if back else 108))<.01 and abs(a['enemies'][enemy][1]-100)<.01
   samples=[]
   for i in range(12):
    time.sleep(.035);raw=p.read(p.symbols['game']+body,52);a=state();samples.append(dict(player_frame=frames()[0],enemy_frame=frames()[enemy+1],body=list(struct.unpack('<13i',raw)),enemy=a['enemies'][enemy][:4]))
    if i in (0,3,6):screenshot(artifacts/(name+'-%d.png'%i))
   traces[name]=samples
   if not back:
    expected=enemy_frames_ref['garcia' if enemy==0 else 'donovan']['front']['frames'][3]['fpg']
    checks[name+'_somersault_survives_release']=any(v['body'][0]==2 and v['enemy_frame']==expected for v in samples)
   time.sleep(1)
   checks[name+'_landing_damage_once']=state()['enemies'][enemy][2]==(86 if back else 88)
 reset()
 result=dict(checks=checks,throw_traces=traces,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Real held/released buttons; debugger positions targets and initial holds. Frame IDs/scripts and body phases inspected in PPSSPP; not physical PSP.')
 (artifacts/'v14-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(checks,indent=2));assert all(checks.values())
finally:p.send(square=False,cross=False,start=False,right=False,left=False,down=False);p.close()


