"""Run rdr8 over every fixture and compare with the committed expectations."""
import sys, os, json, glob, mmap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr9 as rdr8
FX = sys.argv[1]
FLG = 'closure'
n = 0; bad = []; NAMES = []
def cmp(name, got, exp):
    global n; n += 1; NAMES.append(name)
    if got != exp: bad.append((name, got, exp))
def limits_from(args):
    L = {}
    if not args: return L
    m = {'--max-entries':'entries','--max-index-bytes':'index','--max-total-bytes':'total','--max-ratio':'ratio'}
    for k, v in zip(args[::2], args[1::2]): L[m[k]] = int(v)
    return L
def strip(o):
    if isinstance(o, dict): return {k: strip(v) for k, v in o.items() if k != 'message'}
    if isinstance(o, list): return [strip(x) for x in o]
    return o
# bad fixtures
for d, ext in [('core/invalid', False), ('core/invalid', True), ('extended/invalid', True), ('core/attacks', True),
               ('core/hostile', True), ('core/hostile64', True)]:
    for e in sorted(glob.glob(f'{FX}/{d}/*.expect.json')):
        x = json.load(open(e)); base = e[:-len('.expect.json')]
        if os.path.exists(base + '.chst'):
            data = open(base + '.chst', 'rb').read()
        else:
            rc = json.load(open(base + '.recipe.json'))
            p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sparse-' + os.path.basename(base))
            with open(p, 'wb') as f:
                f.truncate(rc['file_length']); f.write(bytes.fromhex(rc['head_hex']))
                f.seek(rc['tail_offset']); f.write(bytes.fromhex(rc['tail_hex']))
            data = mmap.mmap(os.open(p, os.O_RDONLY), 0, prot=mmap.PROT_READ)
        if d == 'core/invalid' and not ext:
            # Core view of a Core invalid fixture: must give the same answer
            pass
        r = rdr8.check(data, ext=ext, limits=limits_from(x.get('args')), flg1=FLG)
        f = rdr8.first(r)
        got = None if f is None else {'rule': f[0], 'category': f[1], 'detail': f[2], 'exit': f[3]}
        cmp(f'{d}/{os.path.basename(base)} ext={ext}', got, {k: x[k] for k in ('rule','category','detail','exit')})
        if 'details' in x: cmp(f'{d}/{os.path.basename(base)} details', [got['detail']], x['details'])
        # list mode: step 11 skipped -> if expected is BLB-6/ZST-1/ZST-2-from-step11, list gives next or success
        rl = rdr8.check(data, ext=ext, mode='list', limits=limits_from(x.get('args')), flg1=FLG)
        fl = rdr8.first(rl)
        if x['rule'] in ('BLB-6','ZST-1') or (x['rule']=='ZST-2' and not os.path.basename(base).endswith('ZST-2-short')):
            cmp(f'{d}/{os.path.basename(base)} list-mode', fl, None)
        elif x['rule'] == 'LIM-5':
            cmp(f'{d}/{os.path.basename(base)} list-mode', fl, None)
        else:
            cmp(f'{d}/{os.path.basename(base)} list-mode', fl and fl[0], x['rule'])
# extract-cases
for e in sorted(glob.glob(f'{FX}/core/extract-cases/*.expect.json')):
    x = json.load(open(e)); data = open(e[:-12] + '.chst', 'rb').read()
    f = rdr8.first(rdr8.check(data, ext=True, flg1=FLG))
    cmp('extract-cases/' + os.path.basename(e), (f[3] if f else 0, f and f[2]), (x['exit'], x.get('detail')))
# N7: selective step 11 on late-blob-hash
data = open(f'{FX}/core/extract-cases/late-blob-hash.chst','rb').read()
r = rdr8.check(data, ext=True, mode='extract', flg1=FLG)
paths = [p.decode() for p in r.paths] if hasattr(r, 'paths') else None
r0 = rdr8.check(data, ext=True, mode='list'); paths = [p.decode() for p in r0.paths]
import fnmatch
sel_docs = {i for i, p in enumerate(paths) if p.startswith('docs/') and p.endswith('.txt') and '/' not in p[5:]}
sel_notes = {i for i, p in enumerate(paths) if p == 'notes.txt'}
cmp('N7 docs/*.txt', rdr8.first(rdr8.check(data, ext=True, mode='extract', selected=sel_docs, flg1=FLG)), None)
cmp('N7 notes.txt', (rdr8.first(rdr8.check(data, ext=True, mode='extract', selected=sel_notes, flg1=FLG)) or [None])[0], 'BLB-6')
# valid fixtures: reports
def reports(data, ext):
    r = rdr8.check(data, ext=ext, flg1=FLG); assert not r.v, r.v
    return {'list': rdr8.list_report(r, ext), 'verify': rdr8.verify_report(r, ext), 'inspect': rdr8.inspect_report(r, ext)}
for d, views in [('core/valid', (True, False)), ('extended/valid', (True,))]:
    for dd in sorted(glob.glob(f'{FX}/{d}/*/')):
        data = open(dd + 'container.chst', 'rb').read()
        for ext in views:
            try: rep = reports(data, ext)
            except AssertionError as ex: cmp(f'{dd} ext={ext} valid', str(ex), None); continue
            for c in ('list', 'verify', 'inspect'):
                if os.path.exists(dd + c + '.json'):
                    cmp(f'{dd}{c} ext={ext}', strip(rep[c]), strip(json.load(open(dd + c + '.json'))))
# compat in the Core view
for e in sorted(glob.glob(f'{FX}/compat/*.expect.json')):
    x = json.load(open(e)); base = e[:-12]; data = open(base + '.chst', 'rb').read()
    r = rdr8.check(data, ext=False, flg1=FLG); f = rdr8.first(r)
    cmp('compat/' + os.path.basename(base), (f[3] if f else 0, f and f[2]), (x['exit'], x['detail']))
    if not f:
        for c, fn in (('list', rdr8.list_report), ('verify', rdr8.verify_report), ('inspect', rdr8.inspect_report)):
            cmp(f'compat/{os.path.basename(base)}.{c}', strip(fn(r, False)), strip(json.load(open(f'{base}.{c}.json'))))
    # Extended view, for information
    fx = rdr8.first(rdr8.check(data, ext=True, flg1=FLG))
    cmp('compat-ext/' + os.path.basename(base), (fx[3] if fx else 0, fx and fx[2]), (x['extended']['exit'], x['extended']['detail']))
for e in sorted(glob.glob(f'{FX}/extended/extract-cases/*.expect.json')):
    x = json.load(open(e)); data = open(e[:-12] + '.chst', 'rb').read()
    f = rdr8.first(rdr8.check(data, ext=True, flg1=FLG))
    cmp('ext-extract-cases/' + os.path.basename(e), (f[3] if f else 0, f and f[0], f and f[2]), (x['exit'], x.get('rule'), x.get('detail')))
print(f'comparisons: {n}, mismatches: {len(bad)}  (flg1={FLG})')
for b in bad: print('MISMATCH', b[0], '\n   got', b[1], '\n   exp', b[2])

import collections, re
c = collections.Counter()
for nm in NAMES:
    k = nm.split('/')[0] if not nm.startswith('/') else ('valid-reports ' + ('extended' if '/extended/' in nm else 'core'))
    if 'list-mode' in nm: k += ' list-mode'
    elif ' ext=False' in nm: k += ' core-view'
    elif ' ext=True' in nm and not nm.startswith('/'): k += ' ext-view'
    if ' details' in nm: k += ' details'
    c[k] += 1
for k, v in sorted(c.items()): print(f'  {k}: {v}')
