import sys, os, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
sys.path.append('/home/jaron/projects/container-format-rs/fixtures/gen')
import rdr8, mk, check as gchk
from mk import fhd, frame, raw, rle, blk
from adv import libz, libz_oneshot
C = {}
C['X ss fcs truncated'] = (b'\x28\xb5\x2f\xfd' + bytes([fhd(fcs_flag=2, ss=1)]) + b'\x00\x20', 100)
C['AC truncated did'] = (b'\x28\xb5\x2f\xfd' + bytes([fhd(did=3)]) + b'\x00' + b'\x01', 100)
C['AD fcs!=raw, header only'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', 1)), 100)
C['AD2 fcs!=raw, header+trunc blk'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', 1)) + b'\x01', 100)
C['AG ss fcs=raw, block 131073'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 200000), blocks=rle(65, 131073) + rle(65, 1000) * 68 + rle(65, 927, 1)), 200000)
C['AH ss fcs=raw, blocks <=128K'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 200000), blocks=rle(65, 131072) + rle(65, 1000) * 68 + rle(65, 928, 1)), 200000)
C['AI ss fcs=raw=9MiB (window>8MiB)'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 9 << 20), blocks=rle(65, 1000) * 9437 + rle(65, (9 << 20) - 9437000, 1)), 9 << 20)
C['AJ RLE output over cap mid-block'] = (frame(fhd(), wd=0x40, blocks=rle(65, 4000) + rle(65, 4193, 1)), 8192)
for name, (st, rawlen) in C.items():
    data = mk.build([(st, rawlen, 1)])
    a = rdr8.first(rdr8.check(data, ext=True)); a = a and a[0]
    b = gchk.check(data); b = b[0] if b else None
    print(f'{name:36s} stored={len(st)} rdr8={a!s:6s} gen={b!s:6s} {"<-- DIFF" if a != b else ""} libzstd: {libz(st, rawlen)}')
    open(os.path.join(H, 'adv', name.split()[0] + '.chst'), 'wb').write(data)
