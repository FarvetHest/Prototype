"""Recover the user's local BK3 IDA database for reproducible asset/AI imports.

Dependency: python-idb==0.8.0. Does not fetch a game image from the internet.
Recovered image stays in the explicitly selected local output directory.
"""
import argparse,hashlib,json
from pathlib import Path
import idb
ap=argparse.ArgumentParser()
ap.add_argument('--idb',type=Path,required=True)
ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args()
with idb.from_file(str(a.idb))as db:
 api=idb.IDAPython(db)
 md5=api.idautils.GetInputFileMD5()
 if isinstance(md5,bytes):md5=md5.hex()
 assert md5.lower()=='f1cb9e887bf4bc512d9535c89e420df7',md5
 data=api.ida_bytes.get_bytes(0,0x300000)
 names={name:address for address,name in api.idautils.Names()}
digest=hashlib.sha256(data).hexdigest()
assert digest=='70d40c55c40a1db40be7e5845aaa60a39b123362b8c48a21cec7ebe6f6d1cd60',digest
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'bk3-recovered.bin').write_bytes(data)
(a.out/'bk3-idb-names.json').write_text(json.dumps(names,indent=2))
(a.out/'bk3-recovery.json').write_text(json.dumps(dict(idb_sha256=hashlib.sha256(a.idb.read_bytes()).hexdigest(),
 image_md5=md5,image_sha256=digest,image_bytes=len(data),names=len(names),parser='python-idb 0.8.0'),indent=2))
print('Recovered and verified local IDB:',len(data),'bytes;',len(names),'named addresses')
