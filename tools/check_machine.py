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


def ram(off,size):return p.read(p.symbols['bk3_work_ram']+off,size)
def ramput(off,fmt,*v):p.req('memory.write',address=p.symbols['bk3_work_ram']+off,base64=base64.b64encode(struct.pack(fmt,*v)).decode())
def stats():return list(struct.unpack('<23I',p.read(p.symbols['bk3_machine_stats'],92)))
def freeze():p.req('cpu.stepping')
def go():p.req('cpu.resume');time.sleep(.09)
try:
 checks['native_selftest']=p.u32('selftest_result')==0
 reset();arrange(40,x=220.);time.sleep(.1)
 freeze()
 v=stats();checks['original_slot_order']=v[4:9]==[0xffdf00,0xffe200,0xffe300,0xffe400,0xffe500]
 checks['SST_ids_big_endian']=ram(0xdf0c,2)==b'\x00\x06' and ram(0xe20c,2)==b'\x00\x0e'
 checks['SST_position_fixed_point']=abs(struct.unpack('>i',ram(0xdf40,4))[0]/131072-state()['player'][0])<.001
 ramput(0xe200,'>H',0);calls=v[13];go();freeze()
 checks['RAM_zero_mode_stops_dispatch']=stats()[13]==calls
 ramput(0xe200,'>H',2);ramput(0xe26c,'>B',23);go();freeze()
 checks['RAM_HP_drives_actor']=state()['enemies'][0][2]==23
 ramput(0xe25c,'>H',600);start=stats()[0];go();freeze();elapsed=stats()[0]-start
 inv=struct.unpack('>H',ram(0xe25c,2))[0];checks['inv_timer_once_per_internal_tick']=inv==600-elapsed and elapsed>=2
 wr(36+8,21);go();freeze();checks['legacy_write_committed_to_RAM']=ram(0xe26c,1)==bytes([21])
 # Unknown object and odd enemy mode must not dispatch arbitrary pointers.
 ramput(0xe20c,'>H',0xffff);before=stats();go();freeze();after=stats()
 checks['unknown_id_fails_closed']=after[3]>before[3] and after[13]==before[13]
 ramput(0xe20c,'>H',14);ramput(0xe200,'>H',3);before=stats();go();freeze();after=stats()
 checks['odd_enemy_mode_fails_closed']=after[3]>before[3] and after[13]==before[13]
 ramput(0xe200,'>H',2);go()
 # Actual buttons traverse the new dispatcher and original state numbers.
 p.send(square=True);seen=set();deadline=time.monotonic()+.35
 while time.monotonic()<deadline:
  seen.add(struct.unpack('>H',ram(0xdf00,2))[0]);time.sleep(.008)
 p.send(square=False);checks['combo_state_connected']=0x14 in seen
 time.sleep(.7);button('cross',.04);freeze();checks['jump_state_connected']=struct.unpack('>H',ram(0xdf00,2))[0]==0x18;go()
 button('start',.04);a=stats()[0];time.sleep(.12);checks['pause_freezes_machine']=stats()[0]==a and ram(0xf505,1)==bytes([1]);button('start',.04)
 result=dict(checks=checks,eboot_sha256=hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),ram_bytes=65536,game_bytes=1840,note='Native MIPS execution: debugger changes actual big-endian SST RAM, not only legacy Game fields. Existing translated handlers remain migration adapters.')
 (artifacts/'machine-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert all(checks.values())
finally:
 p.send(start=False,square=False,cross=False);p.close()
