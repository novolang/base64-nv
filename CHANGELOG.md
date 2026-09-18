# Changelog

Every published version, newest first. This file is on the publish
allow-list, so it travels with the package: it is the only thing a
consumer deciding whether to upgrade can read.

## 0.1.0 — 2026-09-18

**The implementation**, published over the 0.0.x interface.  Every
`pub fn` has a body, no `todo()` remains under `src/`, and every
signature is the one 0.0.2 declared — nothing was added, nothing was
removed and nothing changed shape.  A program written against the
interface compiles unchanged and now does something.

- `base64_core` is arithmetic and nothing else.  The two alphabets are
  four contiguous ranges and two special cases rather than a
  sixty-four-entry list, because a list literal is a heap allocation,
  and the whole point of the module is that it puts nothing on the
  heap.  Every function in it carries `@tier(embedded)`, so a `Str`, a
  list or an unbounded loop introduced there is refused where it is
  written.
- `base64` is that machine with `Bytes` in and `Str` out.  Decoding is
  two passes: the first reads the whole document and keeps nothing, and
  only a document that survives it reaches the caller's buffer.  So
  "nothing is written when the document is refused" is true of every
  refusal and not only of a destination that was too short.
- **A document is refused for its characters before its length.**  A
  MIME document wrapped at 76 characters has a line break in it and a
  length no encoding produces, and both are true at once.  The answer
  names the line break, at its offset, because that is the thing to
  strip.  `decoded_len` is unaffected: it reads the length and the
  trailing `=` and nothing else, as its documentation says.
- **More than two `=` is `B64BadPadding` at the third one.**  Two is
  the longest run RFC 4648 § 3.2 can produce.  The interface named the
  refusal; this release fixes which offset it carries.

**The device claim now runs.**  `tests/embedded_probe.nv` still builds
a Cortex-M4 ELF for `--target=nrf52-qemu`, and the same ELF boots under
`qemu-system-arm -machine mps2-an386` and checks four things against
literals: the size arithmetic, both tables at the two characters where
the alphabets differ, "Man" encoded a byte at a time, and `TWFu`
decoded back.  All four answer `ok`.

**Nothing in `base64_core` allocates**, and `tests/alloc_scan.sh` is
that as a check that can fail.  It reads the compiled output at
`--opt=0` — where nothing has been inlined away — for a call to the
allocator in any of the module's fourteen functions, and finds none.
Two negative controls run beside it: an allocation spliced into the
core has to be named by the scan, and the same splice with the tier
annotation left on has to be refused by the compiler.

**Tested against the standard library.**  `tests/differential_tests.nv`
compares this package with `bytes.to_base64` and `bytes.from_base64`
over 3,000 pseudo-random byte strings, in both directions and through
both the allocating and the write-into-a-buffer entry points.  The same
file is a program, so `novo run` and `novo run --interp` both run the
comparison and a compiled-code bug cannot hide behind an interpreter
that agrees with it.  Every line under `src/` is executed by the
suites; `bash tests/coverage.sh` prints the number.

**One source fix that is not a signature change.**  `src/base64.nv`
gained the `use base64_core` line it always needed.  A type from the
other module is visible with no import; a call is not.  The interface
release had no bodies and therefore no calls, so the missing line only
appeared once there were.  Without it a single-file build resolves
`base64_core.encoder` to this module's own one-argument `encoder`,
which is filed against the toolchain as a separate defect.

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
