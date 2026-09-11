# base64-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`.  Installing this package works;
calling it panics with `not implemented`.

## What this is

RFC 4648 base64, both alphabets, padded and unpadded: encode bytes a
caller already holds into a buffer the caller already owns, decode text
back with a refusal that names the character and the offset, and answer
the two size questions — `encoded_len(n)` and `decoded_len(s)` — so the
caller can allocate before it encodes rather than after.

Two modules.  `base64_core` is the group machine on its own — an
alphabet code, a bit accumulator and a count in a `@value` struct, no
buffer and no allocation, three bytes in and four characters out — and
it compiles for a Cortex-M.  `base64` is that machine with `Bytes` and
`Str` attached, for a caller who has the whole payload already.

## The standard library already has base64 — when do I use which?

`std.codec`'s `Base64` codec calls `bytes.to_base64`, which is an extern
over a host C symbol.  It is the right thing to reach for most of the
time.  This package is for the four cases it does not cover.

| you want | reach for |
| --- | --- |
| a `Str` from some `Bytes` on a host, standard alphabet, padded | `std.codec` — it is one call and it is already linked |
| the **URL-safe** alphabet: a JWT, a WebPush key, a filename | this |
| the **unpadded** form, which is what JWT specifies | this |
| to encode **into a buffer you own**, allocating nothing per call | this |
| to encode or decode a **stream** a chunk at a time | this |
| to run **on a device** | this — `bytes.to_base64` does not link there |
| a refusal that **names the bad character and its offset** | this |
| a refusal for a **non-canonical tail** (RFC 4648 § 3.5) | this |

The last two are worth a sentence each.  A decoder that answers
"invalid" and nothing else leaves a caller printing the whole document
to a log to find out what happened; `B64BadCharacter(at, ch)` lets them
print a caret instead.  And a decoder that accepts `Zh==` as well as
`Zg==` has given a signature, a cache key or a token two spellings —
which is why RFC 4648 § 3.5 says the unused bits of a final quantum are
zero, and why this decoder refuses a document that sets them.

## Adding it, and checking it

```bash
novo pkg add base64-nv        # into your novo.toml
novo pkg build                # type- and effect-check the package
novo test --isolate tests/base64_tests.nv
```

`novo test` is red today and that is the point of the release: every
assertion fails with `not implemented: base64.<fn>`.  They turn green
one at a time as bodies land.

## The one example that will work

```novo
use std.bytes
use base64

fn main() [io]
    println(base64.encode(bytes.from_str("Man"), B64Standard, B64Padded))
    // TWFu — RFC 4648 § 9's own worked example

    match base64.decode("TWFu", B64Standard)
        Ok(b)  => println(bytes.to_hex(b))   // 4d616e
        Err(e) => println(e.message())
```

## The load-bearing interface

`B64Enc` and its three fields, in `base64_core`:

```novo
pub @value
struct B64Enc
    alphabet: Int
    hold: Int
    count: Int
```

Three bytes in, four characters out, and `count` never reaches three
because the third byte completes the group and leaves.  `B64Dec` is its
mirror with a fourth field, `bad`, which latches when a character
outside the alphabet arrives — a `@value` function has nowhere to put a
`Result`, so the refusal rides on the value and `base64` turns it into
one at the boundary.

Everything else is that machine with something attached.  `encode` and
`decode` run it over a whole payload; `encode_into` and `decode_into`
run it into a `Cursor` the caller sized with `encoded_len`; `encoder`
and `decoder` hand the raw value back for a caller streaming chunks or
running on a device.

Two consequences a reviewer should push on:

- **The alphabet is an integer on the device side and an enum on the
  host side.**  A `@value` struct holds integers, and a fieldless enum
  is still a tagged value.  `alphabet_code` is the one function that
  crosses, and it is the same arrangement bitstream-nv uses for its bit
  order.
- **Padding is a property of the document when decoding and an argument
  when encoding.**  `decode` takes no padding argument at all: the
  length and the trailing `=` already say which form it is, and a
  decoder that took the answer as an argument would have two ways to
  disagree with the bytes.

## The layer, and why

`core`.  Everything here is a table lookup and three shifts over bytes
the caller already holds, and no function declares an effect.

It carries `tests/embedded_probe.nv`, so the device claim is **built**
rather than asserted: `base64_core` speaks `Int` and `u8` and nothing
else, and the probe compiles to a Cortex-M4 ELF for
`--target=nrf52-qemu`.  That claim is the whole reason this package
exists beside the standard library — if the probe stopped building,
there would be little left here that `std.codec` does not already do.
`base64` is deliberately outside the probe: it speaks `Bytes` and `Str`,
and one host-only function anywhere in a compilation unit is an
undefined symbol at embedded link time whether or not the firmware calls
it.

## Why this does not depend on bitstream-nv

A reader who has seen bitstream-nv will expect it in the dependency
list, because base64 is six bits at a time and that is what a bit reader
does.  Two reasons it is not there.

The first is arithmetic: base64's group is a **fixed** twenty-four bits
and its alphabet is a table lookup, so the whole encoder is one shift
and four indexed reads.  A general reader that can take any width from 1
to 64 carries a width argument through that inner loop for no gain.

The second is the device claim: the shard audit builds the embedded
probe from the package's own core modules and nothing they depend on, so
a probe that reached a dependency could not be built at all today.  That
limitation is filed against the toolchain rather than designed around
here — but with the first reason standing on its own, there is nothing
to design around.

## The reference implementation

`base64` (Rust, MIT/Apache-2.0) and Python's `base64` module for the
surface, and RFC 4648 for everything else.  Every vector in
`tests/base64_tests.nv` is from § 10's eight-line test suite or § 9's
worked "Man" example, so a reader can check the port against the
specification rather than against this package.

## Status

| function | implemented |
| --- | --- |
| `base64_core.standard`, `.url_safe`, `.group_bytes`, `.group_chars` | no |
| `base64_core.encoded_len`, `.decoded_len`, `.symbol`, `.value` | no |
| `base64_core.encoder`, `.push`, `.finish` | no |
| `base64_core.decoder`, `.feed`, `.close` | no |
| `base64.alphabet_code`, `.B64Error.message` | no |
| `base64.encoded_len`, `.decoded_len` | no |
| `base64.encode`, `.encode_into` | no |
| `base64.decode`, `.decode_into` | no |
| `base64.encoder`, `.decoder` | no |
