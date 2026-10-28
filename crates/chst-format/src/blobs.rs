//! The reader, §13 step 11: each blob's data against its key (BLB-6).
//!
//! Only verify and extract run this step; list and inspect stop after step 10 (F34). The data
//! is streamed through one fixed-size buffer, so memory doesn't grow with a blob's size (G6).

use std::io::{Read, Seek, SeekFrom};

use sha2::{Digest, Sha256};

use crate::error::{Category, Error, detail};
use crate::tables::{Blob, Tables};

/// The size of the read buffer, and so the most this step reads at once.
pub const BLOB_BUFFER_LEN: usize = 64 * 1024;

/// Step 11 for every blob of `tables`, in table order. The first blob whose data doesn't
/// match its key is reported.
///
/// A Core reader accepts only stored blobs (BLB-2), so there is nothing to decode, and the
/// ZST rules of step 11 never apply.
pub fn check_blobs<R: Read + Seek>(src: &mut R, tables: &Tables) -> Result<(), Error> {
    let mut buf = [0u8; BLOB_BUFFER_LEN];
    for (i, blob) in tables.blobs.iter().enumerate() {
        check_blob(src, i, blob, &mut buf)?;
    }
    Ok(())
}

/// BLB-6 for blob `i`: SHA-256 of its `stored_length` bytes at `offset` equals its key.
fn check_blob<R: Read + Seek>(
    src: &mut R,
    i: usize,
    blob: &Blob,
    buf: &mut [u8; BLOB_BUFFER_LEN],
) -> Result<(), Error> {
    src.seek(SeekFrom::Start(blob.offset))
        .map_err(|e| Error::io(&e))?;
    let mut hasher = Sha256::new();
    let mut left = blob.stored_length;
    while left > 0 {
        let n = usize::try_from(left).map_or(BLOB_BUFFER_LEN, |l| l.min(BLOB_BUFFER_LEN));
        let chunk = buf.get_mut(..n).unwrap_or_default();
        src.read_exact(chunk).map_err(|e| Error::io(&e))?;
        hasher.update(&*chunk);
        // n is at most `left`, so this can't wrap.
        left = left.saturating_sub(n as u64);
    }
    if hasher.finalize().as_slice() != blob.key.as_slice() {
        return Err(Error::new(
            Category::Integrity,
            detail::BLOB_HASH,
            format!(
                "blob {i}: its {} bytes at offset {} do not match its key",
                blob.stored_length, blob.offset
            ),
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::io::{Cursor, SeekFrom};

    use super::*;
    use crate::limits::Limits;
    use crate::reader::open;
    use crate::report::build::{Spec, file};
    use crate::tables::Purpose;

    fn tables_of(bytes: &[u8]) -> Tables {
        let l = Limits::default();
        let opened = open(&mut Cursor::new(bytes), &l).unwrap();
        let sections = opened.sections(&l).unwrap();
        opened.tables(&sections, &l, Purpose::Verify).unwrap()
    }

    fn check(bytes: &[u8], tables: &Tables) -> Result<(), Error> {
        check_blobs(&mut Cursor::new(bytes), tables)
    }

    fn is_hash(e: &Error, blob: usize) {
        assert_eq!(
            (e.category(), e.detail()),
            (Category::Integrity, detail::BLOB_HASH)
        );
        assert!(e.message().starts_with(&format!("blob {blob}:")), "{e}");
    }

    const TREE: &[(&str, Option<&[u8]>)] = &[
        ("a", Some(b"first")),
        ("b", Some(b"")),
        ("c", Some(b"third")),
    ];

    #[test]
    fn every_blob_matches_its_key() {
        let bytes = file(&Spec::new(TREE));
        check(&bytes, &tables_of(&bytes)).unwrap();
    }

    #[test]
    fn the_first_blob_that_does_not_match_is_reported() {
        let good = file(&Spec::new(TREE));
        let t = tables_of(&good);
        // Blob 2 alone.
        let mut bytes = good.clone();
        bytes[32 + 5 + 4] ^= 1;
        is_hash(&check(&bytes, &t).unwrap_err(), 2);
        // Blob 0's first byte too: it comes first in table order.
        bytes[32] ^= 1;
        is_hash(&check(&bytes, &t).unwrap_err(), 0);
        // Blob 0's last byte.
        let mut bytes = good;
        bytes[32 + 4] ^= 1;
        is_hash(&check(&bytes, &t).unwrap_err(), 0);
    }

    /// Records the largest read it is asked for.
    struct Counting {
        inner: Cursor<Vec<u8>>,
        largest: usize,
    }

    impl Read for Counting {
        fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
            self.largest = self.largest.max(buf.len());
            self.inner.read(buf)
        }
    }

    impl Seek for Counting {
        fn seek(&mut self, to: SeekFrom) -> std::io::Result<u64> {
            self.inner.seek(to)
        }
    }

    #[test]
    fn a_large_blob_is_read_in_bounded_chunks() {
        let big: Vec<u8> = (0..3 * BLOB_BUFFER_LEN + 7)
            .map(|i| (i % 251) as u8)
            .collect();
        let tree: &[(&str, Option<&[u8]>)] = &[("big", Some(&big))];
        let good = file(&Spec::new(tree));
        let t = tables_of(&good);
        let mut src = Counting {
            inner: Cursor::new(good.clone()),
            largest: 0,
        };
        check_blobs(&mut src, &t).unwrap();
        assert!(src.largest <= BLOB_BUFFER_LEN, "a read of {}", src.largest);
        // A change anywhere in the blob is found: in the first chunk, at a chunk boundary,
        // and in the short last chunk.
        for at in [
            0,
            BLOB_BUFFER_LEN - 1,
            BLOB_BUFFER_LEN,
            3 * BLOB_BUFFER_LEN + 6,
        ] {
            let mut bytes = good.clone();
            bytes[32 + at] ^= 0x80;
            is_hash(&check(&bytes, &t).unwrap_err(), 0);
        }
    }

    #[test]
    fn an_input_that_ends_inside_a_blob_is_io_read() {
        let good = file(&Spec::new(TREE));
        let t = tables_of(&good);
        let e = check(&good[..32 + 7], &t).unwrap_err();
        assert_eq!((e.category(), e.detail()), (Category::Io, detail::IO_READ));
    }
}
