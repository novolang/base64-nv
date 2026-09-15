# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

## 0.0.1 — 2026-09-11

The **interface**, before anyone implements it.  Every signature, every
type and every effect row is published; every body is `todo()`, and the
release is stamped `NOT IMPLEMENTED — interface only`.  Adding this
package works and calling it panics.

- Two modules.  `base64_core` is the twenty-four-bit group machine
  alone — an alphabet code, an accumulator and a count in a `@value`
  struct, three bytes in and four characters out, no buffer and no
  allocation; `base64` is that machine with `Bytes` and `Str` attached.
- Both RFC 4648 alphabets, § 4's standard and § 5's URL-safe, and both
  forms, padded and unpadded.  Encoding takes the padding as an
  argument; decoding reads it off the document, because the length and
  the trailing `=` already say which form it is.
- `encode_into` and `decode_into` write into a `Cursor` the caller
  already owns, and `encoded_len` and `decoded_len` are what the caller
  sized it with.  A destination shorter than the answer is refused with
  both numbers and nothing is written — a partially encoded buffer is
  worse than none, because it looks like a document.
- Four named refusals: a character outside the alphabet with its
  offset, a length no encoding produces, `=` anywhere but the end, and
  a final quantum whose unused bits are set.  The last is RFC 4648
  § 3.5's canonicality rule, and it is the difference between a base64
  string being an identity and being one of two spellings.
- `encoder` and `decoder` hand the raw `@value` state back, which is
  both the streaming surface for a payload larger than memory and the
  handoff to a device.

**The device claim is built**, and it is the reason this package exists
beside `std.codec`.  The standard library's base64 is an extern over a
host C symbol and does not link on a device;
`tests/embedded_probe.nv` compiles this one to a Cortex-M4 ELF for
`--target=nrf52-qemu`, driving both directions a byte at a time.

**No dependency on bitstream-nv**, which is the one a reader will look
for.  base64's group is a fixed twenty-four bits and its alphabet is a
table, so a general variable-width bit reader carries a width argument
through the inner loop for no gain — and the embedded probe is built
from the package's own core modules and nothing they depend on, so a
dependency would cost the device claim on top of that.
