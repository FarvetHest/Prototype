"""Check generated machine metadata against the pinned original, independently."""
import hashlib,json,re
from pathlib import Path
from import_bk3 import ROOT,SHA
p=ROOT
s=(p/'original/vendor/BK3.asm').read_bytes()
audit=json.loads((p/'assets/machine-source.json').read_text())
source=s.decode('latin-1');header=(p/'src/machine_data.h').read_text()
checks={}
checks['pinned_full_source']=hashlib.sha256(s).hexdigest()==audit['source_sha256']==SHA
checks['original_RAM_addresses']=all(audit['constants'][k]==v for k,v in dict(P1CharacterSST=0xffffdf00,P2CharacterSST=0xffffe000,BossObjSST=0xffffe100,EnemyObjSST=0xffffe200).items())
checks['SST_field_offsets']=all(audit['constants'][k]==v for k,v in dict(ObjMode=0,ObjID=12,HPos=64,VPos=68,ObjStatus1=88,InvinsibilityTimer=92,HP=108,GrabHoldTimer=182).items())
checks['every_generated_constant_matches']=all(re.search(r'\bBK3_'+re.escape(k)+r'=0x'+format(v,'x')+r'u,',header) for k,v in audit['constants'].items())
lines=source.splitlines()
checks['state_labels_link_to_exact_source_lines']=all(e['label'] in lines[e['line']-1] for t in audit['tables'].values() for e in t.values())
checks['unresolved_Axel_offsets_not_guessed']=all(('"'+e['label']+'"') not in header for e in audit['tables']['axel'].values() if e.get('unresolved'))
loader=source[source.index('LoadEnemyObj:'):source.index('; End of function LoadEnemyObj')]
checks['six_slots_and_stride_from_loader']=all(v in loader for v in ['(BossObjSST).w,a0','#5,d7','$100(a0),a0','InvinsibilityTimer(a0)','ObjID(a0),d0'])
checks['Zack_capture_dispatch_table']=audit['tables']['zack']['26']['label']=='sub_2C80E' and audit['tables']['zack']['28']['label']=='sub_2C8BA'
death=source[source.index('Enemy_Death:'):source.index('; End of function Enemy_Death')]
disappear=source[source.index('Enemy_Disappear:'):source.index('; End of function Enemy_Disappear')]
checks['original_death_counter_and_blink_bit']=bool(re.search(r'move\.w\s+#\$64,\$68\(a0\)',death) and re.search(r'btst\s+#1,\$69\(a0\)',disappear) and re.search(r'bset\s+#4,\$1E\(a0\)',disappear))
report=dict(checks=checks,source_sha256=SHA,state_entries={k:len(v)for k,v in audit['tables'].items()},note='Source metadata checks, separate from EBOOT integration checks.')
(p/'test-results/machine-source-tests.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2));assert all(checks.values())
