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
        if (status.get('game')or{}).get('id')!='SORL02401':
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
import prepare_sor1_stage as src
checks={};pixel_counts={};special=[]
try:
 checks['selftest']=p.u32('selftest_result')==0
 native_reset();time.sleep(.9);p.req('cpu.stepping')
 wr(184,1);wl(164,'<3i',0,0,0);wl(12,'<i',0);wl(0,'<i',1);wl(16,'<i',0)
 # Keep native view but freeze combat. Fixtures inspect actual submitted VRAM.
 for i in range(4):wr(36*(i+1)+8,0)
 p.req('cpu.resume')
 d=src.dat('dword_5F5C8');ptrs=struct.unpack_from('>8I',d);vram=bytearray(65536)
 for i in [0,2]:
  cmd,addr=ptrs[i:i+2];art=src.kos(src.at(addr));dest=((cmd>>16)&0x3fff)|((cmd&3)<<14);vram[dest:dest+len(art)]=art
 defs=[src.eni(src.at(ptrs[4])),src.eni(src.at(ptrs[5]))];pal=src.palette(src.at(ptrs[7]));maps=[src.expand(n,336)[0]for n in ['off_5F7A8','off_5F9DA']]
 def source_pixel(wx,y):
  color=(0,0,0,255)
  for priority in [0,1]:
   for layer in [1,0]:
    block=maps[layer][(y//16)*336+wx//16];a=defs[layer][block*4+(y%16)//8*2+(wx%16)//8]
    if a>>15!=priority:continue
    sx=wx%8;sy=y%8
    if a&2048:sx=7-sx
    if a&4096:sy=7-sy
    c=(vram[(a&2047)*32+sy*4+sx//2]>>(4 if sx%2==0 else 0))&15
    if c:color=pal[((a>>13)&3)*16+c]
  r,g,b,_=color;return(r>>3)|((g>>2)<<5)|((b>>3)<<11)
 for camera in [0,1024,2048,3072,4096,4896]:
  p.req('cpu.stepping');wl(24,'<f',camera/2);player_x(64.);p.req('cpu.resume');time.sleep(.15)
  p.req('cpu.stepping')
  try:
   raw=p.read(p.u32('presented_buffer'),512*272*2);matched=total=0
   for y in range(43,78,3):
    for x in range(4,388,3):
     wx=camera+x;c=source_pixel(wx,y)
     if not c or any(source_pixel(wx+dx,y+dy)!=c for dx in [-1,0,1]for dy in [-1,0,1]):continue
     sx=x*17//14;sy=y*17//14
     total+=1;matched+=struct.unpack_from('<H',raw,sy*1024+sx*2)[0]==c
   pixel_counts[str(camera)]=dict(matched=matched,total=total)
   checks['native_source_pixels_'+str(camera)]=total>=100 and matched==total
  finally:p.req('cpu.resume')
  screenshot(artifacts/('route1-camera-'+str(camera)+'.png'))
 # Check projection's bound at the far right and alignment of all world layers.
 p.req('cpu.stepping');wl(24,'<f',2448.);player_x(230.);p.req('cpu.resume');time.sleep(.12)
 checks['native_scale_enabled']=p.u32('stage_native_view')==1
 checks['pan_reaches_85']=p.u32('stage_view_pan')==85
 checks['right_edge_is_original_map_end']=p.u32('stage_camera_pixels')==4981
 atlas=(project/'assets/hud.rgba').read_bytes();m=json.loads((project/'assets/hud-manifest.json').read_text())
 for state in range(13):
  wr(552,state*16);time.sleep(.08);p.req('cpu.stepping')
  try:
   raw=p.read(p.u32('presented_buffer'),512*272*2);f=next(v for v in m['frames']if v['file']=='bk3_special' and v['id']==state);matched=total=0
   for y in range(32):
    for x in range(16):
     u=f['u']+x;v=f['v']+y;b=u*4;off=((v//8)*64+b//16)*128+(v%8)*16+b%16;r,g,b,a=atlas[off:off+4]
     if not a:continue
     want=(r>>3)|((g>>2)<<5)|((b>>3)<<11);total+=1;matched+=struct.unpack_from('<H',raw,(8+y)*1024+(166+x)*2)[0]==want
   if state==0:
    total=480;matched=sum(struct.unpack_from('<H',raw,(8+y)*1024+(166+x)*2)[0]==0 for y in range(30)for x in range(16))
   special.append(dict(state=state,matched=matched,total=total));checks['original_special_state_'+str(state)]=matched==total
  finally:p.req('cpu.resume')
 screenshot(artifacts/'original-special-meter.png')
 checks['no_missing_frames']=p.u32('missing_sprite_frames')==0
 result=dict(checks=checks,source_pixel_counts=pixel_counts,special_states=special,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),note='PPSSPP RGB565 framebuffer; reference pixels decoded from pinned SoR1 native layers; only solid interior samples avoid nearest-neighbour edge ambiguities. All opaque special-meter pixels compared in 13 states. Debugger freezes combat and sets cameras/charge; does not prove original enemy scripting or real-hardware FPS.')
 (artifacts/'route1-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:p.close()
