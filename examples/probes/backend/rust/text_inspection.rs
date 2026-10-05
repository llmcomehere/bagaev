//! Generic UTF-8 byte lookup precursor; no source opcode or native ABI change.
use crate::{option_int::OptionInt64, text_value::Text};
/// Zero-based byte position. Negative and out-of-range positions are absent.
/// Byte values are unsigned (0..255); this is not Unicode scalar indexing.
pub fn byte_at(text: Text<'_>, index: i64) -> OptionInt64 {
    if index < 0 || index as u64 >= text.byte_len() as u64 {
        return OptionInt64::none();
    }
    OptionInt64::some(i64::from(text.bytes()[index as usize]))
}
