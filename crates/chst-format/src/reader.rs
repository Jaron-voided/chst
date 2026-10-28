//! The reader, §13 steps 1 to 8: the header, the trailer, the index's location and size, the
//! structure hash, and the header's flags.
//!
//! The rules run in exactly the order of §13, and only the first violation is reported.

use std::io::{Read, Seek, SeekFrom};

use sha2::{Digest, Sha256};

use crate::error::{Category, Error, detail};
use crate::format::{
    HASH_ALG_SHA256, HEADER_LEN, Header, KNOWN_REQUIRED_FLAGS, MAGIC, MAJOR_VERSION,
    MAX_INDEX_LENGTH, MIN_FILE_LEN, TRAILER_LEN, TRAILER_MAGIC, Trailer,
};
use crate::limits::Limits;

/// A container that has passed steps 1 to 8.
#[derive(Debug)]
pub struct Opened {
    pub file_length: u64,
    pub header: Header,
    pub trailer: Trailer,
    /// The index, which the structure hash covers (§5).
    pub index: Vec<u8>,
}

impl Opened {
    /// Step 9 of §13: frames and checks the sections of the index.
    pub fn sections(&self, limits: &Limits) -> Result<crate::sections::Sections, Error> {
        crate::sections::parse_sections(&self.index, &self.header, limits)
    }
}

fn read_array<R: Read, const N: usize>(src: &mut R) -> Result<[u8; N], Error> {
    let mut buf = [0u8; N];
    src.read_exact(&mut buf).map_err(|e| Error::io(&e))?;
    Ok(buf)
}

fn seek_to<R: Seek>(src: &mut R, offset: u64) -> Result<(), Error> {
    src.seek(SeekFrom::Start(offset))
        .map_err(|e| Error::io(&e))?;
    Ok(())
}

/// Runs steps 1 to 8 of §13 over `src`, under `limits`.
///
/// Nothing is allocated in proportion to a declared quantity until TRL-2, LIM-2 and LIM-4
/// have checked it (§10.3). The index is then read into memory, and its size is bounded by
/// the actual length of the input and by both limits.
pub fn open<R: Read + Seek>(src: &mut R, limits: &Limits) -> Result<Opened, Error> {
    // 1. HDR-1
    let file_length = src.seek(SeekFrom::End(0)).map_err(|e| Error::io(&e))?;
    if file_length < MIN_FILE_LEN {
        return Err(Error::new(
            Category::NotAContainer,
            detail::HDR_TOO_SHORT,
            format!("the file is {file_length} bytes; a container is at least {MIN_FILE_LEN}"),
        ));
    }
    seek_to(src, 0)?;
    let header_bytes: [u8; HEADER_LEN as usize] = read_array(src)?;
    let header = Header::parse(&header_bytes);

    // 2. HDR-2
    if header.magic != MAGIC {
        return Err(Error::new(
            Category::NotAContainer,
            detail::HDR_MAGIC,
            "the file does not start with the container magic",
        ));
    }
    // 3. HDR-3
    if header.major_version != MAJOR_VERSION {
        return Err(Error::new(
            Category::Unsupported,
            detail::HDR_MAJOR_VERSION,
            format!("major version {} is not supported", header.major_version),
        ));
    }
    // 4. HDR-4
    if header.hash_alg != HASH_ALG_SHA256 {
        return Err(Error::new(
            Category::Unsupported,
            detail::HDR_HASH_ALG,
            format!("hash algorithm {} is not supported", header.hash_alg),
        ));
    }

    // 5. TRL-1
    seek_to(src, file_length - TRAILER_LEN)?;
    let trailer_bytes: [u8; TRAILER_LEN as usize] = read_array(src)?;
    let trailer = Trailer::parse(&trailer_bytes);
    if trailer.trailer_magic != TRAILER_MAGIC {
        return Err(Error::new(
            Category::Malformed,
            detail::TRL_MAGIC,
            "the trailer magic is wrong",
        ));
    }

    // 6. TRL-2, then LIM-2, then LIM-4
    let in_range = trailer.index_offset >= HEADER_LEN
        && trailer
            .index_offset
            .checked_add(trailer.index_length)
            .and_then(|end| end.checked_add(TRAILER_LEN))
            == Some(file_length);
    if !in_range {
        return Err(Error::new(
            Category::Malformed,
            detail::TRL_INDEX_RANGE,
            format!(
                "the index (offset {}, length {}) does not fit the file ({file_length} bytes)",
                trailer.index_offset, trailer.index_length
            ),
        ));
    }
    if trailer.index_length > MAX_INDEX_LENGTH {
        return Err(Error::new(
            Category::Malformed,
            detail::LIM_INDEX_SIZE,
            format!(
                "the index is {} bytes; the hard maximum is {MAX_INDEX_LENGTH}",
                trailer.index_length
            ),
        ));
    }
    if trailer.index_length > limits.max_index_bytes {
        return Err(Error::new(
            Category::LimitExceeded,
            detail::LIMIT_INDEX_SIZE,
            format!(
                "the index is {} bytes; the limit is {}",
                trailer.index_length, limits.max_index_bytes
            ),
        ));
    }

    // 7. Read the index, then TRL-3. The length is now at most the file's length, 2^32 and
    // the configured limit, and the allocation is fallible.
    let index = read_index(src, trailer.index_offset, trailer.index_length)?;
    let mut hasher = Sha256::new();
    hasher.update(header_bytes);
    hasher.update(&index);
    hasher.update(&trailer_bytes[..16]);
    if hasher.finalize().as_slice() != trailer.structure_hash.as_slice() {
        return Err(Error::new(
            Category::Integrity,
            detail::TRL_HASH,
            "the structure hash does not match the header, the index and the trailer",
        ));
    }

    // 8. HDR-6, then HDR-5
    if header.required_flags & !KNOWN_REQUIRED_FLAGS != 0 {
        return Err(Error::new(
            Category::Unsupported,
            detail::HDR_REQUIRED_FLAG,
            format!(
                "required feature flags {:#x} are not implemented",
                header.required_flags & !KNOWN_REQUIRED_FLAGS
            ),
        ));
    }
    if header.reserved != [0, 0, 0] {
        return Err(Error::new(
            Category::Malformed,
            detail::HDR_RESERVED,
            "the reserved header bytes are not zero",
        ));
    }

    Ok(Opened {
        file_length,
        header,
        trailer,
        index,
    })
}

/// An empty vector with room for `length` bytes, or `io.memory` if the memory can't be had.
fn allocate_index(length: u64) -> Result<Vec<u8>, Error> {
    let cannot_hold = || {
        Error::new(
            Category::Io,
            detail::IO_MEMORY,
            format!("cannot allocate {length} bytes of memory for the index"),
        )
    };
    let len = usize::try_from(length).map_err(|_| cannot_hold())?;
    let mut index = Vec::new();
    index.try_reserve_exact(len).map_err(|_| cannot_hold())?;
    Ok(index)
}

fn read_index<R: Read + Seek>(src: &mut R, offset: u64, length: u64) -> Result<Vec<u8>, Error> {
    let mut index = allocate_index(length)?;
    seek_to(src, offset)?;
    let got = src
        .take(length)
        .read_to_end(&mut index)
        .map_err(|e| Error::io(&e))?;
    if u64::try_from(got).ok() != Some(length) {
        return Err(Error::new(
            Category::Io,
            detail::IO_READ,
            format!("the input ended after {got} of {length} index bytes"),
        ));
    }
    Ok(index)
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use super::*;

    /// A file of `len` bytes with a valid magic, version and hash algorithm, and a trailer
    /// with the given `index_offset` and `index_length`. Its structure hash is not valid.
    fn file(len: usize, index_offset: u64, index_length: u64) -> Vec<u8> {
        let mut f = vec![0u8; len];
        f[..8].copy_from_slice(&MAGIC);
        f[8] = 1;
        f[12] = 1;
        let t = len - 56;
        f[t..t + 8].copy_from_slice(&index_offset.to_le_bytes());
        f[t + 8..t + 16].copy_from_slice(&index_length.to_le_bytes());
        f[t + 48..].copy_from_slice(&TRAILER_MAGIC);
        f
    }

    fn fail(bytes: Vec<u8>, limits: &Limits) -> Error {
        match open(&mut Cursor::new(bytes), limits) {
            Ok(_) => panic!("expected a failure"),
            Err(e) => e,
        }
    }

    fn is(e: &Error, category: Category, detail: &str) {
        assert_eq!((e.category(), e.detail()), (category, detail), "{e}");
    }

    #[test]
    fn a_short_file_is_not_a_container() {
        for len in [0, 1, 31, 87] {
            let e = fail(vec![0u8; len], &Limits::default());
            is(&e, Category::NotAContainer, detail::HDR_TOO_SHORT);
        }
    }

    #[test]
    fn header_rules_run_in_order() {
        let l = Limits::default();
        let mut f = file(88, 32, 0);
        f[0] ^= 1;
        f[8] = 2;
        f[12] = 9;
        is(
            &fail(f.clone(), &l),
            Category::NotAContainer,
            detail::HDR_MAGIC,
        );
        f[0] ^= 1;
        is(
            &fail(f.clone(), &l),
            Category::Unsupported,
            detail::HDR_MAJOR_VERSION,
        );
        f[8] = 1;
        is(
            &fail(f.clone(), &l),
            Category::Unsupported,
            detail::HDR_HASH_ALG,
        );
    }

    #[test]
    fn the_trailer_magic_comes_before_the_index_range() {
        let mut f = file(88, 0, u64::MAX);
        f[87] ^= 1;
        is(
            &fail(f, &Limits::default()),
            Category::Malformed,
            detail::TRL_MAGIC,
        );
    }

    #[test]
    fn the_index_range_is_checked_without_overflow() {
        let l = Limits::default();
        for (offset, length) in [
            (31, 1),
            (0, 0),
            (32, 1),
            (u64::MAX, 1),
            (32, u64::MAX),
            (32, u64::MAX - 55),
            (u64::MAX - 55, 0),
        ] {
            let e = fail(file(88, offset, length), &l);
            is(&e, Category::Malformed, detail::TRL_INDEX_RANGE);
        }
    }

    #[test]
    fn the_configurable_limit_is_checked_against_the_declared_index() {
        let l = Limits {
            max_index_bytes: 9,
            ..Limits::default()
        };
        let e = fail(file(88 + 10, 32, 10), &l);
        is(&e, Category::LimitExceeded, detail::LIMIT_INDEX_SIZE);
        // At the limit, the rules go on and fail later, at the structure hash.
        let e = fail(file(88 + 9, 32, 9), &l);
        is(&e, Category::Integrity, detail::TRL_HASH);
    }

    /// An input that claims `len` bytes but holds only a header and a trailer; every other
    /// byte reads as zero.
    struct Virtual {
        len: u64,
        pos: u64,
        head: Vec<u8>,
        tail: Vec<u8>,
    }

    impl Read for Virtual {
        fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
            let tail_start = self.len - self.tail.len() as u64;
            let mut n = 0;
            for slot in buf.iter_mut() {
                if self.pos >= self.len {
                    break;
                }
                *slot = if self.pos < self.head.len() as u64 {
                    self.head[self.pos as usize]
                } else if self.pos >= tail_start {
                    self.tail[(self.pos - tail_start) as usize]
                } else {
                    0
                };
                self.pos += 1;
                n += 1;
            }
            Ok(n)
        }
    }

    impl Seek for Virtual {
        fn seek(&mut self, to: SeekFrom) -> std::io::Result<u64> {
            self.pos = match to {
                SeekFrom::Start(n) => n,
                SeekFrom::End(d) => self.len.saturating_add_signed(d),
                SeekFrom::Current(d) => self.pos.saturating_add_signed(d),
            };
            Ok(self.pos)
        }
    }

    #[test]
    fn the_hard_maximum_comes_before_the_configurable_limit() {
        for (index_length, category, d) in [
            (
                MAX_INDEX_LENGTH + 1,
                Category::Malformed,
                detail::LIM_INDEX_SIZE,
            ),
            (
                MAX_INDEX_LENGTH,
                Category::LimitExceeded,
                detail::LIMIT_INDEX_SIZE,
            ),
        ] {
            let len = 32 + index_length + 56;
            let small = file(88, 32, index_length);
            let mut src = Virtual {
                len,
                pos: 0,
                head: small[..32].to_vec(),
                tail: {
                    let mut t = small[small.len() - 56..].to_vec();
                    t[..8].copy_from_slice(&32u64.to_le_bytes());
                    t
                },
            };
            // Both LIM-2 and LIM-4 are violated at the first size (limit 0), and nothing
            // of the 4 GiB index is read or allocated.
            let l = Limits {
                max_index_bytes: 0,
                ..Limits::default()
            };
            let e = open(&mut src, &l).unwrap_err();
            is(&e, category, d);
        }
    }

    #[test]
    fn an_index_that_cannot_be_allocated_is_io_memory() {
        // No vector can hold more than isize::MAX bytes, so this fails at once with
        // CapacityOverflow, before the allocator is asked for anything. On a target where
        // usize is narrower than u64, the conversion fails instead.
        let e = allocate_index(u64::MAX).unwrap_err();
        is(&e, Category::Io, detail::IO_MEMORY);
        let e = allocate_index(usize::MAX as u64).unwrap_err();
        is(&e, Category::Io, detail::IO_MEMORY);
        // A small request is granted, and nothing is read into it yet.
        let v = allocate_index(16).unwrap();
        assert!(v.is_empty() && v.capacity() >= 16);
    }

    #[test]
    fn a_failing_source_is_an_io_error() {
        struct Broken;
        impl Read for Broken {
            fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::Error::other("boom"))
            }
        }
        impl Seek for Broken {
            fn seek(&mut self, _: SeekFrom) -> std::io::Result<u64> {
                Ok(1000)
            }
        }
        let e = open(&mut Broken, &Limits::default()).unwrap_err();
        is(&e, Category::Io, detail::IO_READ);
    }
}
