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
        if (status.get('game')or{}).get('id')!='SORL00016':
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
traces=[]
try:
 checks['selftest']=p.u32('selftest_result')==0
 native_reset();a=lv();checks['first_wave_starts']=a['enabled']==1 and a['wave']==0 and a['locked']==1 and a['slots']==15
 p.send(right=True);time.sleep(.4);p.send(right=False);time.sleep(.1)
 checks['camera_locked_during_fight']=lv()['camera']==0 and state()['won']==0
 button('start',.04);before=lv();time.sleep(.12);checks['level_pauses']=lv()['timer']==before['timer'] and state()['paused']==1
 # Verify actual rendered background pixels across all six RAM pages.
 stage=(project/'assets/stage.rgb565').read_bytes();max_batches=0
 for cam in [0,511,1023,1535,2047,2372]:
  p.req('memory.write',address=p.symbols['level']+24,base64=base64.b64encode(struct.pack('<f',cam/2)).decode());time.sleep(.08)
  raw=p.read(p.u32('presented_buffer'),512*272*2);ok=True
  for x in [0,31,32,239,479]:
   world=cam+x;page,u=divmod(world,512);sy=64;byte=u*2;off=page*262144+((sy//8)*64+byte//16)*128+(sy%8)*16+byte%16
   ok &= raw[96*1024+x*2:96*1024+x*2+2]==stage[off:off+2]
  checks['rendered_source_pixels_'+str(cam)]=bool(ok);max_batches=max(max_batches,p.u32('stage_draw_count'))
  if cam in (511,1535,2372):screenshot(artifacts/('stage-scroll-%d.png'%cam))
 checks['background_at_most_two_batches']=max_batches<=2 and p.u32('stage_slice_count')<=16
 p.req('memory.write',address=p.symbols['level']+24,base64=base64.b64encode(struct.pack('<f',0)).decode());button('start',.04)
 manifest=json.loads((project/'assets/stage-manifest.json').read_text())
 checks['all_RAM_pages_uploaded']=all(hashlib.sha256(p.read(p.symbols['stage_texture']+i*262144,262144)).hexdigest()==v for i,v in enumerate(manifest['page_sha256']))
 for wave in range(5):
  before=lv();checks['wave_%d_locked'%wave]=before['wave']==wave and before['locked']==1
  if wave==1:
   p.req('cpu.stepping');wr(44,17);wr(8,0);wr(800,0);p.req('memory.write_u32',address=p.symbols['flow']+4,value=1);p.req('cpu.resume');time.sleep(.15)
   checks['death_offers_continue']=struct.unpack('<i',p.read(p.symbols['flow'],4))[0]==3
   button('start',.04)
   checks['continue_keeps_wave_camera_damage']=lv()['camera']==before['camera'] and lv()['wave']==1 and state()['enemies'][0][2]==17 and state()['player'][2]==100
  kill_wave();after=lv();score=p.u32('ui_score');traces.append(dict(wave=wave,camera=after['camera'],score=score,clears=after['clears']))
  if wave<4:
   checks['wave_%d_GO_and_no_early_victory'%wave]=after['go']==1 and after['locked']==0 and after['slots']==0 and state()['won']==0
  else:
   checks['last_wave_spawns_boss_before_exit']=after['locked']==1 and after['slots']==2 and after['go']==0 and state()['enemies'][1][2]==240 and after['generation']==6 and state()['won']==0
   checks['last_wave_score_preserved_at_boss_spawn']=score==8000
   screenshot(artifacts/'boss-entry.png')
   p.req('cpu.stepping');wr(80,140);wr(8,0);wr(800,0);p.req('memory.write_u32',address=p.symbols['flow']+4,value=1);p.req('cpu.resume');time.sleep(.15);button('start',.04)
   checks['boss_continue_preserves_HP_camera']=state()['enemies'][1][2]==140 and lv()['camera']==1186 and lv()['slots']==2
   # The missing 100 HP must count as damage before the final kill.
   checks['boss_damage_score']=p.u32('ui_score')==8500
   kill_wave();after=lv();checks['boss_defeat_score']=p.u32('ui_score')==9400
   checks['boss_defeat_unlocks_GO']=after['locked']==0 and after['go']==1 and after['slots']==0
  if wave==0:
   deadline=time.monotonic()+1
   while ((lv()['timer']//15)&1) and time.monotonic()<deadline:time.sleep(.02)
   screenshot(artifacts/'level-GO.png')
  if wave<4:
   walk_to_wave(wave+1);after=lv()
   checks['wave_%d_spawn_preserves_score_HP'% (wave+1)]=p.u32('ui_score')==score and state()['player'][2]==80 and all(e[2]==40 for e in state()['enemies']) and after['generation']==wave+2
   screenshot(artifacts/('wave-%d.png'%(wave+2)))
 p.send(right=True);deadline=time.monotonic()+8
 while not lv()['finished'] and time.monotonic()<deadline:time.sleep(.08)
 p.send(right=False);time.sleep(.1)
 checks['five_waves_and_exit_clear']=lv()['finished']==1 and lv()['camera']==1186 and lv()['clears']==6 and state()['won']==1 and struct.unpack('<i',p.read(p.symbols['flow'],4))[0]==5
 screenshot(artifacts/'stage-clear.png');native_reset()
 checks['new_run_resets_level']=lv()['wave']==0 and lv()['camera']==0 and lv()['clears']==0 and lv()['generation']==1 and p.u32('ui_score')==0
 # Source attack choice while closing in on an airborne target.
 for family,index,ai_level,expected in [('Donovan',1,5,10),('DonovanLow',1,4,8),('Garcia',0,5,8)]:
  reset();arrange(100,x=220.);p.send(cross=True);time.sleep(.15);p.send(cross=False);p.req('cpu.stepping')
  p.req('memory.write',address=p.symbols['game']+36*(index+1),base64=base64.b64encode(struct.pack('<2f7i',82.,100.,100,-1,0,0,0,0,0)).decode())
  wr(576+index*56,2);wr(592+index*56,ai_level)
  p.req('cpu.resume');time.sleep(.04)
  checks['source_approach_'+family]=struct.unpack('<i',p.read(p.symbols['game']+576+index*56,4))[0]==expected
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,level_trace=traces,max_background_batches=max_batches,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Movement and wave gates use real input; HP/deaths are debugger fixtures to traverse the full level quickly. Framebuffer pixels compared with the source background at page boundaries. Not physical PSP performance.')
 (artifacts/'level-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(right=False,left=False,start=False);p.close()

