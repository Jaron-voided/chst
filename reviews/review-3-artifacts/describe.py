import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdr8
FX = '/home/jaron/projects/container-format-rs/fixtures'
def walk(b):
    """structural description of a frame"""
    out = []
    rule, h = rdr8.zstd_header(b)
    if rule:
        return f'header -> {h}; first 12 bytes {b[:12].hex()}'
    out.append(f"hdr fhd={h['fhd']:#04x} win={h['window']} fcs={h['fcs']} ss={h['ss']} cks={h['cks']} hdrlen={h['hdr_end']}")
    p = h['hdr_end']; nb = 0; tot = 0; kinds = {}
    while p + 3 <= len(b):
        bh = int.from_bytes(b[p:p+3], 'little'); p += 3; last, bt, bs = bh & 1, (bh >> 1) & 3, bh >> 3
        kinds[(bt, bs)] = kinds.get((bt, bs), 0) + 1; nb += 1
        p += 1 if bt == 1 else (bs if bt in (0, 2) else 0)
        if bt != 2: tot += bs
        if last or bt == 3: break
    out.append(f'blocks={nb} kinds(type,size)x={dict(list(kinds.items())[:4])} rawRLEtotal={tot} end={p} len={len(b)} lastflag={last}')
    return '; '.join(out)
names = sys.argv[1:]
for n in names:
    f = f'{FX}/{n}.chst'; d = open(f, 'rb').read(); x = json.load(open(f'{FX}/{n}.expect.json'))
    r = rdr8.check(d, ext=True, mode='list', all_=True)
    print(f'== {n}  ({len(d)} bytes)  expect {x["rule"]}/{x["detail"]}  mutation: {x.get("mutation")}')
    for i, B in enumerate(r.blobs):
        if B['enc'] == 1:
            st = d[B['off']:B['off']+B['st']]
            print(f'   blob{i} stored={B["st"]} raw={B["raw"]} : {walk(st)}')
            res = rdr8.zstd_frame(st, B['raw']); print('   step-11 result:', res[0], res[1] if res[0] else '')
