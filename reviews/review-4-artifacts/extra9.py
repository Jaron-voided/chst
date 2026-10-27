"""Extra round-9 checks with rdr9: time bomb, LIM-6 boundary, wrapping multiply, M7 fixtures, M2 extract-case."""
import sys, os, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr9
FX = '/home/jaron/projects/container-format-rs/fixtures'
t = time.time(); d = open('tb.chst','rb').read()
r = rdr9.check(d); print('time bomb:', rdr9.first(r), f'{time.time()-t:.2f}s')
# structure of the bomb
B = [b for b in r.blobs if b['enc']==1][0]
print('  bomb blob stored', B['st'], 'raw', B['raw'], 'raw-st', B['raw']-B['st'], 'ratio ok (LIM-6 default)?', B['raw'] <= 1000*B['st'])
zc = open(f'{FX}/extended/valid/zstd-compressed/container.chst','rb').read()
r = rdr9.check(zc); enc = [(b['st'], b['raw']) for b in r.blobs if b['enc']==1]; print('zstd-compressed encoded blobs (stored, raw):', enc)
M = 2**64 - 1
print('exact, --max-ratio 2^64-1:', rdr9.first(rdr9.check(zc, limits={'ratio': M})))
def u64_wrap_violates(raw, lim, st): return raw > (lim*st) % 2**64
def u64_checked_violates(raw, lim, st): return True if lim*st >= 2**64 else raw > lim*st
def u64_sat_violates(raw, lim, st): return raw > min(lim*st, 2**64-1)
for name, f in [('wrapping (Rust release `*`)', u64_wrap_violates), ('checked->violation', u64_checked_violates), ('saturating', u64_sat_violates)]:
    print(f'  {name}: AC-X-ZSTD-2 case max-ratio 2^64-1 violates?', any(f(raw, M, st) for st, raw in enc))
st, raw = enc[0]
L = -(-2**64 // st)   # ceil(2^64/st): product wraps to a tiny value
print(f'  a limit that exposes a wrapping multiply: --max-ratio {L}; exact violates? {raw > L*st}; wrapped product {(L*st)%2**64}; wrapping violates? {u64_wrap_violates(raw, L, st)}')
for n in ('ZST-2-second-frame', 'ZST-2-trailing-skippable'):
    dd = open(f'{FX}/extended/invalid/{n}.chst','rb').read(); print(n, rdr9.first(rdr9.check(dd)))
    from compression import zstd
    rr = rdr9.check(dd); b = [b for b in rr.blobs if b['enc']==1]
    for b in b:
        s = dd[b['off']:b['off']+b['st']]
        try: out = zstd.decompress(s); print('   one-shot libzstd output', len(out), 'raw', b['raw'])
        except Exception as e: print('   one-shot libzstd error', e)
e = f'{FX}/extended/extract-cases/zstd-corrupt-block'
dd = open(e + '.chst','rb').read(); rr = rdr9.check(dd, all_=False)
print('zstd-corrupt-block verify:', rdr9.first(rr))
for b in rr.blobs:
    if b['enc']==1:
        s = dd[b['off']:b['off']+b['st']]
        import hashlib
        print('  hash ok?', hashlib.sha256(s).digest()==b['key'], ' frame alone:', rdr9.zstd_frame(s, b['raw'])[0], ' byte7', hex(s[7]), 'stored', b['st'])
