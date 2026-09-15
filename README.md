# base64-nv

Base64 writes arbitrary bytes as text, using an alphabet of sixty-four
characters that survives channels which are not binary-safe. It is
specified in [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648), which
also defines a second alphabet for use in URLs and filenames. This
package brings both alphabets to novo-lang, in a form that also builds
for a microcontroller.

**Status: NOT IMPLEMENTED — interface only.** Every function is declared
with its full signature, but every body is a `todo()` that panics when
called. The package is published so its design can be reviewed and
depended on before it is implemented. Version 0.1.0 will be the first
working release.

## What base64 is

Base64 reads the message three bytes at a time. Those twenty-four bits
are split into four groups of six bits. Each six-bit group is one
character of the alphabet, so three bytes become four characters. Three
bytes at a time is called a **quantum**, and it is the unit the whole
format is built from.

A message whose length is not a multiple of three ends in a short
quantum. One leftover byte becomes two characters and two leftover bytes
become three. The unused low bits of the last character are zero. RFC
4648 section 3.5 calls an encoding that sets them **non-canonical**,
because two different documents then decode to the same bytes.

**Padding** is the `=` character, added to bring the last quantum up to
four characters. RFC 4648 section 3.2 requires it unless the
specification using base64 says otherwise. It carries no information:
the length of the text already says how many bytes the last quantum
held. JSON Web Tokens and most other URL-safe uses drop it.

The two alphabets differ in two characters out of sixty-four. Section 4
defines the standard alphabet, which ends `+` and `/`. Section 5 defines
the URL- and filename-safe alphabet, which ends `-` and `_`. Those two
characters are exactly the ones that need escaping in a URL query, in a
path segment and in a filename.

| Quantity | Value |
| --- | --- |
| Bytes in one quantum | 3 |
| Characters one quantum encodes to | 4 |
| Bits one character carries | 6 |
| Characters in an alphabet | 64 |
| Characters the two alphabets differ in | 2 |
| Characters `n` bytes encode to, padded | `4 * ceil(n / 3)` |
| Characters `n` bytes encode to, unpadded | `4 * (n / 3)`, plus 0, 2 or 3 |
| Padding character | `=` |
| Longest run of padding on a document | 2 |

## Install

```
novo pkg add base64-nv
```

## Example

```novo
use std.bytes
use base64

fn main() [io]
    // Encode three bytes with the standard alphabet, padded.
    // RFC 4648 section 9 walks this example through by hand.
    println(base64.encode(bytes.from_str("Man"), B64Standard, B64Padded))

    // Decode the same text back. The alphabet is given; the padding is
    // read off the document.
    match base64.decode("TWFu", B64Standard)
        // The three bytes, as hexadecimal.
        Ok(b)  => println(bytes.to_hex(b))
        // The character that was wrong, and where it was.
        Err(e) => println(e.message())
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a `not implemented: base64.<fn>`
panic. The tests are the specification the implementation will have to
satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `base64_core` | The quantum machine: an alphabet code, a bit accumulator and a count, with the two alphabet tables, the size arithmetic, and one step in each direction. It holds no buffer and allocates nothing. |
| `base64` | The same machine over a whole payload: `Bytes` in and `Str` out, the two enums a host caller reads, the five named refusals, and the calls that write into a buffer the caller owns. |

## How to choose an entry point

**`base64.encode` and `base64.decode` take the whole payload.** Each
allocates the result and hands it back. This is the call for a program
that already holds the bytes and wants the text.

**`base64.encode_into` and `base64.decode_into` write into a `Cursor`
you already own.** Size the destination with `base64.encoded_len` or
`base64.decoded_len` first. This is the call for a program that encodes
on a schedule and wants to allocate once.

**`base64.encoder` and `base64.decoder` hand back the raw state.** Feed
it with `base64_core.push` or `base64_core.feed`, and end it with
`base64_core.finish` or `base64_core.close`. This is the call for a
payload larger than memory, and the handoff to a device.

**`base64_core` on its own is the whole format for firmware.** It takes
and answers integers, so it links on a device. See "Running on a
microcontroller".

## The rules a user needs

1. **The alphabet is an argument on every call that could care.** A
   document decoded with the wrong alphabet does not fail quietly. It
   produces different bytes, or a refusal naming a character that is in
   the other table. RFC 4648 sections 4 and 5 define the two.
2. **Encoding takes the padding as an argument, and decoding does not.**
   The length of the text and its trailing `=` characters already say
   which form a document is in. RFC 4648 section 3.2 is the rule.
3. **A final quantum whose unused bits are set is refused.** That is
   `B64NonCanonicalTail`, from RFC 4648 section 3.5. `QQ` and `QR` both
   describe the single byte `A`, so a program using base64 text as a
   signature, a cache key or a token needs one spelling per value.
4. **A character outside the alphabet is refused with its offset.**
   `B64BadCharacter(at, ch)` gives the position and the byte. Line
   breaks are such characters. RFC 4648 section 3.3 says to reject them
   unless the specification using base64 says otherwise, so a caller
   decoding MIME strips them first.
5. **A length whose remainder is one is not an encoding of anything.**
   One leftover character carries six bits of a byte that has eight.
   `B64BadLength` reports it, and `base64_core.decoded_len` answers a
   negative number for the same input.
6. **`encode_into` and `decode_into` write nothing when the destination
   is short.** They answer `B64BufferTooSmall(need, have)` instead. A
   half-written buffer is worse than an empty one, because it looks like
   a document.
7. **The core modules report a refusal on the value, not as a
   `Result`.** `B64Dec.bad` latches when a bad character arrives, and
   `B64Drain.ok` is false for the step that failed. A `@value` function
   has nowhere to put a `Result` payload, so `base64` converts at the
   boundary.
8. **`=` is never fed to `base64_core.feed`.** Padding is a property of
   the quantum rather than a character with a value, and
   `base64_core.close` is what reads it.
9. **The alphabet crosses between the halves as an integer.**
   `base64.alphabet_code` converts the enum a host caller reads into the
   integer a `@value` struct can hold. A program that sets a stream up
   on a host and encodes it on a device needs that one call.

## Running on a microcontroller

novo-lang lets a package state which of its modules can run on a device
with no heap allocator, and the compiler checks that claim on every
build. Here the claim covers `base64_core` and nothing else. It takes
and answers `Int` and `u8`, and it holds no buffer.

`tests/embedded_probe.nv` is that claim as a program that either builds
or does not. It builds today:

```bash
novo build --target=nrf52-qemu tests/embedded_probe.nv
```

The probe produces a Cortex-M4 executable that reads both tables, runs
the size arithmetic, and drives the encoder and the decoder a byte at a
time. It builds and it is not run: every function it calls is a `todo()`
today.

**A device cannot use the `base64` module.** That module speaks `Bytes`
and `Str`, and the embedded runtime defines neither. One host-only
function anywhere in a compilation unit is an undefined symbol at link
time on a device, whether or not the firmware calls it. That is why the
package is two modules.

## What is not included

- **Base32 and base16.** RFC 4648 sections 6 and 8 define them, and this
  package is section 4 and section 5 only. `bytes.to_hex` in the
  standard library is base16.
- **MIME's line breaks.** RFC 2045 wraps base64 at 76 characters, and
  this decoder treats a line break as a character outside the alphabet.
  Strip the breaks before decoding.
- **A dependency on
  [bitstream-nv](https://novo-lang.org/packages/bitstream-nv).** A base64
  quantum is a fixed twenty-four bits and the alphabet is a table
  lookup, so a general variable-width bit reader would carry a width
  argument through the inner loop for nothing.
- **A decoder that guesses the alphabet.** Both alphabets share
  sixty-two characters, so most documents are valid under either and
  decode to different bytes.
- **Any input or output.** Every function here is arithmetic over bytes
  the caller already holds.

## Related packages

- `std.codec` in the standard library has a `Base64` codec, which calls
  `bytes.to_base64`. That is an extern over a host C symbol: it is one
  call, it is already linked, and it is the standard alphabet, padded,
  on a host. It has no URL-safe alphabet, no unpadded form, no size
  arithmetic and no streaming form, and it does not link on a device.
- [bech32-nv](https://novo-lang.org/packages/bech32-nv) is another text
  encoding of bytes, at five bits per character with a checksum over the
  result. Base64 has no checksum.
- [ulid-nv](https://novo-lang.org/packages/ulid-nv) encodes a 128-bit
  identifier in Crockford base32, which is a different alphabet for a
  fixed-size value.
- [bitstream-nv](https://novo-lang.org/packages/bitstream-nv) reads and
  writes runs of bits of any width, which is the general form of the
  six-bit read this package does.

## Tests

```bash
novo test tests/base64_tests.nv        # 26 tests
```

Every vector is RFC 4648's own. Section 10 is the specification's test
suite, the eight lines from `BASE64("")` to `BASE64("foobar")`. Section 9
is the worked `Man` example the encoder table is derived from. A
document that passes here is one any conforming decoder reads.

The suite asserts that both alphabets encode the eight vectors, that the
two tables differ in exactly two characters, that a document decoded
with the wrong alphabet is refused by offset, that the unpadded form is
the padded one without the `=`, that both forms decode without being
told which they are, that padding in the middle is refused, that a
single leftover character is refused, that a final quantum with its
unused bits set is refused, that a newline is a character outside the
alphabet, that the size functions answer what a caller sizes a buffer
with, that the writing calls refuse a short destination, and that the
host enum maps onto the integer the device half stores.

The tests compile today and fail at run, each on the `not implemented`
panic that is its body. That is the expected state of an interface
release. They turn green one at a time as bodies land.

## Implementation status

| Item | Implemented |
| --- | --- |
| `base64_core.standard`, `.url_safe`, `.group_bytes`, `.group_chars` | no |
| `base64_core.encoded_len`, `.decoded_len`, `.symbol`, `.value` | no |
| `base64_core.encoder`, `.push`, `.finish` | no |
| `base64_core.decoder`, `.feed`, `.close` | no |
| `base64.alphabet_code`, `B64Error.message` | no |
| `base64.encoded_len`, `.decoded_len` | no |
| `base64.encode`, `.encode_into` | no |
| `base64.decode`, `.decode_into` | no |
| `base64.encoder`, `.decoder` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
