//! Byte layout of the header and the trailer (FORMAT_SPEC §4 and §5).
//!
//! All integers are fixed-width little-endian (D3). The parsers take fixed-size arrays and
//! read at constant offsets, so no input can make them fail.

/// Length of the header.
pub const HEADER_LEN: u64 = 32;
/// Length of the trailer.
pub const TRAILER_LEN: u64 = 56;
/// HDR-1: the shortest possible file.
pub const MIN_FILE_LEN: u64 = HEADER_LEN + TRAILER_LEN;
/// Header `magic`.
pub const MAGIC: [u8; 8] = [0x43, 0x48, 0x53, 0x54, 0x0D, 0x0A, 0x1A, 0x00];
/// Trailer `trailer_magic`.
pub const TRAILER_MAGIC: [u8; 8] = [0x00, 0x1A, 0x0A, 0x0D, 0x54, 0x53, 0x48, 0x43];
/// The only `major_version` this specification defines.
pub const MAJOR_VERSION: u16 = 1;
/// `hash_alg` 1 is SHA-256 (§12.4).
pub const HASH_ALG_SHA256: u8 = 1;
/// LIM-2: the hard maximum of `index_length`.
pub const MAX_INDEX_LENGTH: u64 = 1 << 32;
/// The `required_flags` bits this reader implements. A Core reader implements none (§12.1).
pub const KNOWN_REQUIRED_FLAGS: u64 = 0;

/// Copies `M` bytes starting at `at`. Bytes beyond the end of `bytes` read as zero, which
/// can't happen for the constant offsets used here (the unit tests cover every field).
fn field<const N: usize, const M: usize>(bytes: &[u8; N], at: usize) -> [u8; M] {
    let mut out = [0u8; M];
    for (o, b) in out.iter_mut().zip(bytes.iter().skip(at)) {
        *o = *b;
    }
    out
}

/// The 32-byte header.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Header {
    pub magic: [u8; 8],
    pub major_version: u16,
    pub minor_version: u16,
    pub hash_alg: u8,
    pub reserved: [u8; 3],
    pub required_flags: u64,
    pub optional_flags: u64,
}

impl Header {
    pub fn parse(bytes: &[u8; HEADER_LEN as usize]) -> Header {
        Header {
            magic: field(bytes, 0),
            major_version: u16::from_le_bytes(field(bytes, 8)),
            minor_version: u16::from_le_bytes(field(bytes, 10)),
            hash_alg: u8::from_le_bytes(field(bytes, 12)),
            reserved: field(bytes, 13),
            required_flags: u64::from_le_bytes(field(bytes, 16)),
            optional_flags: u64::from_le_bytes(field(bytes, 24)),
        }
    }
}

/// The 56-byte trailer.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Trailer {
    pub index_offset: u64,
    pub index_length: u64,
    pub structure_hash: [u8; 32],
    pub trailer_magic: [u8; 8],
}

impl Trailer {
    pub fn parse(bytes: &[u8; TRAILER_LEN as usize]) -> Trailer {
        Trailer {
            index_offset: u64::from_le_bytes(field(bytes, 0)),
            index_length: u64::from_le_bytes(field(bytes, 8)),
            structure_hash: field(bytes, 16),
            trailer_magic: field(bytes, 48),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_fields_are_read_at_their_offsets() {
        let mut b = [0u8; 32];
        b[..8].copy_from_slice(&MAGIC);
        b[8..10].copy_from_slice(&0x0201u16.to_le_bytes());
        b[10..12].copy_from_slice(&0x0403u16.to_le_bytes());
        b[12] = 5;
        b[13..16].copy_from_slice(&[6, 7, 8]);
        b[16..24].copy_from_slice(&0x1112_1314_1516_1718u64.to_le_bytes());
        b[24..32].copy_from_slice(&0x2122_2324_2526_2728u64.to_le_bytes());
        let h = Header::parse(&b);
        assert_eq!(h.magic, MAGIC);
        assert_eq!(h.major_version, 0x0201);
        assert_eq!(h.minor_version, 0x0403);
        assert_eq!(h.hash_alg, 5);
        assert_eq!(h.reserved, [6, 7, 8]);
        assert_eq!(h.required_flags, 0x1112_1314_1516_1718);
        assert_eq!(h.optional_flags, 0x2122_2324_2526_2728);
    }

    #[test]
    fn trailer_fields_are_read_at_their_offsets() {
        let mut b = [0u8; 56];
        b[..8].copy_from_slice(&0x0102_0304_0506_0708u64.to_le_bytes());
        b[8..16].copy_from_slice(&0x1112_1314_1516_1718u64.to_le_bytes());
        for (i, x) in b[16..48].iter_mut().enumerate() {
            *x = 0x80 + i as u8;
        }
        b[48..].copy_from_slice(&TRAILER_MAGIC);
        let t = Trailer::parse(&b);
        assert_eq!(t.index_offset, 0x0102_0304_0506_0708);
        assert_eq!(t.index_length, 0x1112_1314_1516_1718);
        assert_eq!(t.structure_hash[0], 0x80);
        assert_eq!(t.structure_hash[31], 0x9F);
        assert_eq!(t.trailer_magic, TRAILER_MAGIC);
    }
}
