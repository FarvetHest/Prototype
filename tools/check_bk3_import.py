"""Verify complete source pin, index coverage, references and reproducibility."""
import gzip, hashlib, json
from import_bk3 import ROOT, SHA, build

p = ROOT/'original'
raw = (p/'vendor/BK3.asm').read_bytes()
lock = json.loads((p/'bk3.lock.json').read_text())
saved = json.loads(gzip.decompress((p/'source-index.json.gz').read_bytes()))
rebuilt = build(raw)
assert saved == rebuilt
assert lock['sha256'] == hashlib.sha256(raw).hexdigest() == SHA
assert sum(saved['categories'].values()) == saved['lines']
names = {label['name'] for label in saved['labels']}
assert {'Obj_Zack', 'Obj_Blondie', 'Obj_Electra', 'Chk_EnemyGrab'} <= names
assert all(set(r['targets']) <= names for r in saved['references'])
assert all(a['end_line']+1 == b['line'] for a,b in zip(saved['labels'],saved['labels'][1:]))
try:
    build(raw+b'\n')
except ValueError:
    pass
else:
    raise AssertionError('Revision mismatch was accepted')
report = dict(source_sha256=SHA, checks=dict(full_source_pin=True, deterministic_index=True,
              all_lines_classified=True, reference_targets_exist=True,
              contiguous_label_spans=True, known_objects=True, wrong_revision_rejected=True),
              lines=saved['lines'], labels=len(saved['labels']), reference_lines=len(saved['references']))
(ROOT/'test-results/bk3-import-tests.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
