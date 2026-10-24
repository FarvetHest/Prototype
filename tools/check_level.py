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
        if (status.get('game')or{}).get('id')!='SORL00020':
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
try:
 checks['selftest']=p.u32('selftest_result')==0
 native_reset();checks['starts_with_two_not_four']=st()['spawned']==2 and lv()['slots']==3 and not lv()['locked']
 checks['initial_entries_finish']=wait_entry()
 # Hold a real survivor while the queue fills a different slot. No global combat reset.
 p.req('cpu.stepping');wr(44,17);wr(1492,10000);wr(824,10000)
 p.req('memory.write',address=p.symbols['game'],base64=base64.b64encode(struct.pack('<2f',64.,100.)).decode())
 p.req('memory.write',address=p.symbols['game']+36,base64=base64.b64encode(struct.pack('<2f',70.,100.)).decode());retire(1);p.req('cpu.resume')
 p.send(right=True);time.sleep(.13);p.send(right=False);time.sleep(.08)
 checks['reinforcement_before_full_clear']=st()['spawned']>=3 and st()['overlap']>=2 and state()['enemies'][0][2]==17
 checks['reinforcement_preserves_live_grab']=moves()[16]==0 and lv()['camera']==0
 score=p.u32('ui_score');wr(116,38);time.sleep(.1);checks['reused_slot_damage_scores']=p.u32('ui_score')==score+10
 screenshot(artifacts/'stream-reinforcement.png')
 # Reproduce the old release condition: player at x220 against a locked midpoint.
 native_reset();p.req('cpu.stepping');wl(24,'<f',512.);wl(188,'<2i',10,0);wl(196,'<i',0);wl(200,'<i',10);wl(132,'<I',0);player_x(220.);wr(824,10000);p.req('cpu.resume');time.sleep(.06)
 checks['midpoint_gate_holds_live_enemies']=lv()['camera']==512 and lv()['locked']==1
 p.req('cpu.stepping');world=lv()['camera']+state()['player'][0];retire(0);retire(1);p.req('cpu.resume')
 motion=[];deadline=time.monotonic()+.55
 while time.monotonic()<deadline:
  p.req('cpu.stepping');a=lv();b=st();x=state()['player'][0];motion.append((a['timer'],a['camera'],x,b['camera_step']));p.req('cpu.resume');time.sleep(.035)
 checks['unlock_does_not_teleport']=all(0<=v[3]<=3 for v in motion) and motion[0][1]-512<=3*max(1,motion[0][0])
 checks['unlock_preserves_player_world_X']=all(abs(c+x-world)<.01 for _,c,x,_ in motion)
 checks['unlock_spawns_next_encounter_immediately']=st()['gate']==1 and st()['spawned']>=11 and lv()['camera']>512
 # Actual rendered source pixels at all page boundaries; pause makes this independent of scrolling.
 native_reset();time.sleep(.9);button('start',.04);stage=(project/'assets/stage.rgb565').read_bytes();max_batches=0
 for cam in [0,511,1023,1535,2047,2372]:
  wl(24,'<f',cam/2);time.sleep(.08);raw=p.read(p.u32('presented_buffer'),512*272*2);ok=True
  for x in [0,31,32,239,479]:
   worldx=cam+x;page,u=divmod(worldx,512);sy=64;byte=u*2;off=page*262144+((sy//8)*64+byte//16)*128+(sy%8)*16+byte%16
   ok &= raw[96*1024+x*2:96*1024+x*2+2]==stage[off:off+2]
  checks['source_pixels_'+str(cam)]=bool(ok);max_batches=max(max_batches,p.u32('stage_draw_count'))
 checks['at_most_two_background_batches']=max_batches<=2
 # Traverse with real Right input. Debugger kills one arrived enemy at a time to accelerate fights.
 native_reset();wr(824,10000);p.send(right=True);deadline=time.monotonic()+70;next_hit=0;max_slots=0;moving_with_enemies=False;empty_at=None;max_empty_walk=0;last=None;bounded=True;continued=False
 while time.monotonic()<deadline:
  p.req('cpu.stepping');a=lv();b=st();g=state();boss=struct.unpack('<i',p.read(p.symbols['level']+40,4))[0];entry=struct.unpack('<I',p.read(p.symbols['level']+132,4))[0]
  alive=[i for i,e in enumerate(g['enemies'])if e[2]>0];max_slots=max(max_slots,a['slots'].bit_count());moving_with_enemies |= bool(alive and b['camera_step']>0)
  if last:
   dt=a['timer']-last[0];bounded &= a['camera']>=last[1] and a['camera']-last[1]<=3*dt+.01
  last=(a['timer'],a['camera']);wx=a['camera']+g['player'][0]
  if not alive and b['cue']<20:
   if empty_at is None:empty_at=wx
  elif empty_at is not None:max_empty_walk=max(max_empty_walk,wx-empty_at);empty_at=None
  if not traces or traces[-1]['cue']!=b['cue']:traces.append(dict(cue=b['cue'],camera=a['camera'],score=p.u32('ui_score'),live=len(alive)))
  if boss==1:p.req('cpu.resume');break
  if time.monotonic()>=next_hit and alive:
   eligible=[i for i in alive if not(entry&(1<<i))]
   if eligible:retire(eligible[0]);next_hit=time.monotonic()+.28
  p.req('cpu.resume');time.sleep(.04)
 p.send(right=False);time.sleep(.1);a=lv();b=st();boss=struct.unpack('<i',p.read(p.symbols['level']+40,4))[0]
 checks['all_20_cues_reach_boss']=boss==1 and b['cue']==20 and b['spawned']==20 and lv()['slots']==2
 checks['camera_moves_during_fights']=moving_with_enemies
 checks['camera_speed_bounded_entire_route']=bounded
 checks['never_more_than_four_slots']=max_slots<=4
 checks['short_gaps_between_encounters']=max_empty_walk<=160
 checks['score_8000_before_boss']=p.u32('ui_score')==8000
 screenshot(artifacts/'stream-boss-entry.png');checks['boss_entry_finishes']=wait_entry()
 # Continue retains the queue/camera, surviving boss and pickup masks.
 before=st();cam=lv()['camera'];p.req('cpu.stepping');wr(80,140);wr(8,0);wr(800,0);p.req('memory.write_u32',address=p.symbols['flow']+4,value=1);p.req('cpu.resume');time.sleep(.15);button('start',.04)
 checks['continue_preserves_stream_boss']=st()['cue']==before['cue'] and st()['spawned']==20 and lv()['camera']==cam and state()['enemies'][1][2]==140
 p.req('cpu.stepping');retire(1);wr(824,10000);p.req('cpu.resume');time.sleep(.1)
 checks['boss_defeat_scores_9400']=p.u32('ui_score')==9400
 p.send(right=True);deadline=time.monotonic()+8
 while not lv()['finished'] and time.monotonic()<deadline:time.sleep(.05)
 p.send(right=False);checks['exit_fade_and_stage_clear']=lv()['finished']==1 and state()['won']==1 and lv()['camera']==1186 and struct.unpack('<i',p.read(p.symbols['flow'],4))[0]==5
 screenshot(artifacts/'stage-clear.png');native_reset();checks['new_run_resets_queue']=st()['cue']==2 and st()['spawned']==2 and st()['retired']==0 and lv()['camera']==0 and p.u32('ui_score')==0
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,release_trace=motion,cue_trace=traces,max_slots=max_slots,max_empty_walk_pixels=max_empty_walk*2,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='Camera/world conservation and stream traversal use real Right input; debugger kills arrived enemies to accelerate progression and fixtures arrange a held survivor/midpoint release. Distances use half-pixel world units. Not hardware timing.')
 (artifacts/'level-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.send(right=False,left=False,start=False,square=False);p.close()
