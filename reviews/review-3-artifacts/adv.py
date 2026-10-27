"""Adversarial Zstandard frames: rdr8 vs the generator's check.py vs libzstd (compression.zstd)."""
import sys, os, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
sys.path.append('/home/jaron/projects/container-format-rs/fixtures/gen')
import rdr8, mk, check as gchk
from compression import zstd as Z
from mk import fhd, frame, raw, rle, blk
def x64(b): return (rdr8.xxh64(b) & 0xFFFFFFFF).to_bytes(4, 'little')
R = 8192
C = {}
C['D ss fcs=9MiB!=raw'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 9 << 20), blocks=rle(65, R, 1)), R)
C['E wd=9MiB fcs!=raw'] = (frame(fhd(fcs_flag=1), wd=(13 << 3) | 1, fcsb=struct.pack('<H', 100), blocks=rle(65, R, 1)), R)
C['F fcs!=raw + reserved btype'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', 8193 - 256), blocks=blk(3, 10, b'', 1)), R)
C['G fcs=raw + dictid 7'] = (frame(fhd(fcs_flag=1, did=1), wd=0x40, didb=b'\x07', fcsb=struct.pack('<H', R - 256), blocks=rle(65, R, 1)), R)
C['H fcs!=raw + dictid 7'] = (frame(fhd(fcs_flag=1, did=1), wd=0x40, didb=b'\x07', fcsb=struct.pack('<H', 5), blocks=rle(65, R, 1)), R)
C['I 2-byte fcs ok'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', R - 256), blocks=rle(65, R, 1)), R)
C['J unused bit4'] = (frame(fhd(fcs_flag=1, unused=1), wd=0x40, fcsb=struct.pack('<H', R - 256), blocks=rle(65, R, 1)), R)
C['K window exactly 8MiB'] = (frame(fhd(), wd=(13 << 3), blocks=rle(65, R, 1)), R)
C['K2 window 8MiB+1MiB'] = (frame(fhd(), wd=(13 << 3) | 1, blocks=rle(65, R, 1)), R)
C['N wd=1KiB, RLE blocks 2048'] = (frame(fhd(), wd=0x00, blocks=rle(65, 2048) * 3 + rle(65, 2048, 1)), R)
C['N2 wd=1KiB, RAW block 1500'] = (frame(fhd(), wd=0x00, blocks=raw(os.urandom(4)) + rle(66, 1000)*6 + raw(b'z'*1500) + rle(66, R-4-6000-1500, 1)), R)
C['S fcs=raw, ss=1, RLE block > fcs window? no: equal'] = (frame(fhd(fcs_flag=1, ss=1), fcsb=struct.pack('<H', R - 256), blocks=rle(65, R, 1)), R)
good = frame(fhd(), wd=0x40, blocks=rle(65, R, 1))
C['T trailing skippable frame'] = (good + struct.pack('<II', 0x184D2A50, 2) + b'zz', R)
C['U two frames'] = (frame(fhd(), wd=0x40, blocks=rle(65, R // 2, 1)) * 2, R)
C['V no last block'] = (frame(fhd(), wd=0x40, blocks=rle(65, R)), R)
C['W fcs=raw output short'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', R - 256), blocks=rle(65, R - 1, 1)), R)
C['X ss fcs truncated'] = (b'\x28\xb5\x2f\xfd' + bytes([fhd(fcs_flag=2, ss=1)]) + b'\x00\x20', R)
C['Y checksum ok'] = (frame(fhd(cks=1), wd=0x40, blocks=rle(65, R, 1), cksum=x64(b'A' * R)), R)
C['Y2 checksum truncated'] = (frame(fhd(cks=1), wd=0x40, blocks=rle(65, R, 1), cksum=x64(b'A' * R)[:3]), R)
C['Z 8-byte fcs ok'] = (frame(fhd(fcs_flag=3), wd=0x40, fcsb=struct.pack('<Q', R), blocks=rle(65, R, 1)), R)
C['AA did present = 0'] = (frame(fhd(did=2), wd=0x40, didb=b'\0\0', blocks=rle(65, R, 1)), R)
C['AB legacy v0.7 magic'] = (b'\x27\xb5\x2f\xfd' + good[4:], R)
C['AC wd=1KiB truncated did'] = (b'\x28\xb5\x2f\xfd' + bytes([fhd(did=3)]) + b'\x00' + b'\x01', R)
C['AD fcs!=raw, header only'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', 1)), R)
C['AE fcs==raw, header only + pad'] = (frame(fhd(fcs_flag=1), wd=0x40, fcsb=struct.pack('<H', R-256)) + b'\0', R)
C['AF zero-size raw last + RLE'] = (frame(fhd(), wd=0x40, blocks=raw(b'') + rle(65, R, 1)), R)
C['AG ss window=fcs=raw, block > 128K'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 200000), blocks=rle(65, 131073) + rle(65, 200000-131073, 1)), 200000)
C['AH ss fcs=raw=200000 blocks 128K'] = (frame(fhd(fcs_flag=2, ss=1), fcsb=struct.pack('<I', 200000), blocks=rle(65, 131072) + rle(65, 200000-131072, 1)), 200000)
def libz(st, rawlen):
    try:
        d = Z.ZstdDecompressor(options={Z.DecompressionParameter.window_log_max: 23})
        out = d.decompress(st, max_length=rawlen + 1)
        return f'ok len={len(out)} eof={d.eof} unused={len(d.unused_data)}'
    except Exception as e: return f'err {e}'
def libz_oneshot(st):
    try: return f'ok len={len(Z.decompress(st))}'
    except Exception as e: return f'err {e}'
diffs = 0
for name, (st, rawlen) in C.items():
    data = mk.build([(st, rawlen, 1)])
    a = rdr8.first(rdr8.check(data, ext=True)); a = a and a[0]
    b = gchk.check(data); b = b[0] if b else None
    flag = '' if a == b else '   <-- DIFFERENT'
    diffs += a != b
    print(f'{name:40s} rdr8={a!s:6s} gen={b!s:6s} libzstd-stream: {libz(st, rawlen)} | one-shot: {libz_oneshot(st)}{flag}')
    open(os.path.join(H, 'adv', name.split()[0] + '.chst'), 'wb').write(data)
print('cases', len(C), 'rdr8/gen differences', diffs)
