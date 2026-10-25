"""Compile the exact PSP AI executor as a host DLL and record deterministic probes.

Windows: --cc PATH/TO/tcc.exe. Requires the locally generated development bank.
The reference checks CPU execution parity, not complete live combat coverage.
"""
import argparse,ctypes,hashlib,json,os,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--cc',type=Path,required=True)
a=ap.parse_args()
out=ROOT/'test-results';out.mkdir(exist_ok=True)
dll=out/('bk3vm-host.dll'if os.name=='nt'else'bk3vm-host.so')
flags=['-DM68K_EMULATE_'+v+'=0'for v in ['010','EC020','020','030','040','PMMU']]
subprocess.run([str(a.cc.resolve()),'-shared',*flags,'-DM68K_INSTRUCTION_HOOK=1',
 '-o',str(dll),str(ROOT/'src/bk3vm.c'),
 str(ROOT/'src/vendor/musashi/m68kcpu.c'),str(ROOT/'src/vendor/musashi/m68kops.c')],check=True)
lib=ctypes.CDLL(str(dll.resolve()))
fields=['ready','error','id','ticks','instructions','max_instructions','reads','writes',
 'pc','fault_address','completed','passed','requested_id','requested_ticks','end_x','end_y','mode','animation']
class Stats(ctypes.Structure):_fields_=[(n,ctypes.c_uint32)for n in fields]
stats=Stats.in_dll(lib,'bk3vm_stats')
bank=ROOT/'build/bk3-ai.dev.bin'
assert lib.bk3vm_init(str(bank.resolve()).encode()),stats.error
probes=[]
for oid in range(14,78,2):
 assert lib.bk3vm_probe(oid,240)==0,(oid,stats.error,stats.pc,stats.fault_address)
 probes.append({n:getattr(stats,n)for n in ['id','ticks','instructions','max_instructions','end_x','end_y','mode','animation']})
report=dict(bank_sha256=hashlib.sha256(bank.read_bytes()).hexdigest(),
 source_sha256=hashlib.sha256((ROOT/'src/bk3vm.c').read_bytes()).hexdigest(),
 sources={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()for f in [ROOT/'src/bk3vm.c',ROOT/'src/bk3vm.h',ROOT/'src/bk3vm_data.h',*sorted((ROOT/'src/vendor/musashi').glob('*.c')),*sorted((ROOT/'src/vendor/musashi').glob('*.h'))]},probes=probes)
(ROOT/'assets/bk3-vm-reference.json').write_text(json.dumps(report,indent=2))
(out/'bk3-host-tests.json').write_text(json.dumps(report,indent=2))
print('PASS: 32 original object-handler probes compiled from the PSP runtime source')
