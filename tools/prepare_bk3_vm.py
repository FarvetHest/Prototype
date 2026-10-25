"""Create a development AI bank from the user's locally recovered BK3 image.

This bank is not a bootable game image. Native AI integration is still in
development; release packaging must not include it until that work is verified.
"""
import argparse, hashlib, json, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser()
ap.add_argument('--rom',type=Path,required=True)
ap.add_argument('--names',type=Path,required=True)
a=ap.parse_args()
r=bytearray(a.rom.read_bytes())
assert hashlib.sha256(r).hexdigest()=='70d40c55c40a1db40be7e5845aaa60a39b123362b8c48a21cec7ebe6f6d1cd60'
n=json.loads(a.names.read_text())
entries=[struct.unpack_from('>I',r,n['Obj_Enemy']+(i-14)*2)[0]for i in range(14,78,2)]
hooks=['PlaySound','GetArt','PlayRoutine','Chk_CharacterCollision','Chk_EnemyCollision']
header='/* Generated from the pinned BK3 IDA database. */\n'
header+='static const unsigned bk3vm_entries[32]={'+','.join(hex(x)for x in entries)+'};\n'
for key in hooks+['Data_Hit_Collision','Data_Atk_Collision']:header+='#define BK3VM_'+key+' '+hex(n[key])+'u\n'
(ROOT/'src/bk3vm_data.h').write_text(header)
# Omit boot vectors/header, player raw graphics and the sound program. All
# original object routines, profile tables and mapping scripts stay untouched.
excluded=[(0,0x200),(0x50000,0x110000),(0x1a8000,0x200000)]
for lo,hi in excluded:r[lo:hi]=bytes(hi-lo)
fnv=2166136261
for b in r:fnv=((fnv^b)*16777619)&0xffffffff
bank=b'BKA1'+struct.pack('<II',len(r),fnv)+r
out=ROOT/'build';out.mkdir(exist_ok=True)
(out/'bk3-ai.dev.bin').write_bytes(bank)
(ROOT/'assets/bk3-vm-source.json').write_text(json.dumps(dict(
    development_only=True, source_sha256=hashlib.sha256(a.rom.read_bytes()).hexdigest(),
    bank_sha256=hashlib.sha256(bank).hexdigest(), excluded_ranges=excluded,
    hooks={key:n[key]for key in hooks}, entries=entries,
    musashi_commit='313ebf1bd9f4d0d93341eb5ce21fd8a119e9dbdd'),indent=2))
print('Development bank:',out/'bk3-ai.dev.bin',len(bank),'bytes')
