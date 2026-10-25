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
def values(name,n):return list(struct.unpack('<'+'I'*n,p.read(p.symbols[name],n*4)))
def write(name,v,offset=0):p.req('memory.write_u32',address=p.symbols[name]+offset,value=v)
try:
 deadline=time.monotonic()+30
 while p.u32('frame_count')<2:
  assert time.monotonic()<deadline,'Startup did not reach rendering'
  time.sleep(.1)
 reference=json.loads((project/'assets/bk3-vm-reference.json').read_text())
 for name,digest in reference['sources'].items():assert hashlib.sha256((project/name).read_bytes()).hexdigest()==digest,name
 assert reference['source_sha256']==hashlib.sha256((project/'src/bk3vm.c').read_bytes()).hexdigest()
 assert reference['bank_sha256']==hashlib.sha256((project/'build/bk3-ai.dev.bin').read_bytes()).hexdigest()
 report={'eboot_sha256':hashlib.sha256((project/'build/EBOOT.PBP').read_bytes()).hexdigest(),'selftest':p.u32('selftest_result'),'vm_startup':values('bk3vm_stats',14),'graphics':values('bk3gfx_stats',7),'probes':[]}
 assert report['selftest']==0
 assert report['vm_startup'][0]==1 and report['vm_startup'][11]==32
 assert report['graphics'][:4]==[1,0,25,3276800]
 for oid in range(14,78,2):
  write('bk3vm_stats',240,52);write('bk3vm_stats',oid,48)
  deadline=time.monotonic()+10
  while True:
   v=values('bk3vm_stats',14)
   if not v[12] and v[2]==oid and v[3]==240:break
   assert not v[1] and time.monotonic()<deadline,(oid,v)
   time.sleep(.02)
  assert v[1]==0 and v[6:8]==[0,0],(oid,v)
  end=values('bk3vm_stats',18)
  actual=dict(id=oid,ticks=end[3],instructions=end[4],max_instructions=end[5],end_x=end[14],end_y=end[15],mode=end[16],animation=end[17])
  expected=next(r for r in reference['probes']if r['id']==oid)
  assert actual==expected,(actual,expected)
  report['probes'].append(actual)
 report['checks']={'native_selftest':True,'all_32_handlers':len(report['probes'])==32,'host_mips_match':True,'no_bad_memory':True,'all_25_t4_pages_checked':True,'zero_additional_vram':True}
 report['scope']='Isolated object-handler probes with source animation/profile tables. Native scene/collision hooks are stubbed; this is not proof of complete live AI integration or hardware FPS.'
 (artifacts/'bk3-runtime-tests.json').write_text(json.dumps(report,indent=2))
 print('PASS:',len(report['probes']),'host/MIPS matches; 25 T4 pages; native selftest 0')
finally:p.close()
