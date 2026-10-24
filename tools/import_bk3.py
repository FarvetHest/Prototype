"""Import the complete pinned IDA listing; index source, not machine semantics.

No ROM or automatically translated C is produced. Run from any directory.
"""
import argparse, collections, gzip, hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = 'ab4fcf0be4c9b5bac1f60f1d863c2cb6b781c5fb157dad72574c9755534409c3'
LABEL = re.compile(r'^([A-Za-z_][\w.$]*):\s*(.*)$')
TOKEN = re.compile(r'\b[A-Za-z_][\w.$]*\b')

def build(raw):
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError('Different BK3 revision: refusing to mix original tables and code')
    lines = raw.decode('latin-1').splitlines()
    labels, counts = [], collections.Counter()
    for number, line in enumerate(lines, 1):
        code = line.split(';', 1)[0].strip()
        m = LABEL.match(code)
        if m:
            name, code = m.groups()
            labels.append(dict(name=name, line=number))
        op = code.split(None, 1)[0].lower() if code else ''
        kind = ('empty_or_comment' if not op else 'equate' if op == 'equ' else
                'data' if op.startswith(('dc.', 'dcb.', 'ds.')) else 'code_or_directive')
        counts[kind] += 1
    names = {entry['name'] for entry in labels}
    xrefs = []
    for number, line in enumerate(lines, 1):
        code = line.split(';', 1)[0].strip()
        m = LABEL.match(code)
        if m:
            code = m.group(2)
        # Lexical references include tables/offset expressions, not just calls.
        refs = sorted(set(TOKEN.findall(code)) & names)
        if refs:
            xrefs.append(dict(line=number, targets=refs))
    for i, label in enumerate(labels):
        label['end_line'] = labels[i+1]['line']-1 if i+1 < len(labels) else len(lines)
    return dict(schema=1, source_sha256=SHA, bytes=len(raw), lines=len(lines),
                categories=dict(sorted(counts.items())), labels=labels, references=xrefs,
                note='Lexical source index. Label spans are not inferred function boundaries; no control-flow or CPU semantics inferred.')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    args = ap.parse_args()
    raw = args.source.read_bytes()
    index = build(raw)
    out = ROOT/'original'
    (out/'vendor').mkdir(parents=True, exist_ok=True)
    (out/'vendor/BK3.asm').write_bytes(raw)
    encoded = json.dumps(index, separators=(',', ':'), ensure_ascii=True).encode()
    (out/'source-index.json.gz').write_bytes(gzip.compress(encoded, mtime=0))
    lock = dict(repository='https://github.com/gsaurus/sor-disassemblies',
                commit='4dd719f3ed5c24c86deee616b56cea885e3113d7',
                path='Assemblies/Bare Knuckle 3 (J) [!].asm', sha256=SHA,
                imported='vendor/BK3.asm', bytes=len(raw), lines=index['lines'],
                labels=len(index['labels']), reference_lines=len(index['references']),
                categories=index['categories'])
    (out/'bk3.lock.json').write_text(json.dumps(lock, indent=2)+'\n')
    print(json.dumps(lock, indent=2))

if __name__ == '__main__':
    main()
