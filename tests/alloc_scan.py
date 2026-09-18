#!/usr/bin/env python3
"""Read the emitted LLVM for base64-nv's allocation probe and say
whether any function in `base64_core` can put a cell on the heap.

Run by tests/alloc_scan.sh, three times: once on the package as it
stands, and twice on copies with an allocation spliced into the core,
which the scan and the tier checker respectively have to catch.  A check
that cannot fail is not a check.

The IR is emitted at `--opt=0` on purpose.  At the default optimisation
level the whole probe inlines into `novo_main`, there is no function
left to attribute an allocation to, and the scan would pass by vacuity.
"""
import re
import sys

# Every way a function can put a cell on the heap.  `novo_alloc*` is the
# direct one; the other four allocate INSIDE the runtime, so a grep for
# the first alone would call a per-character boxing loop allocation-free
# — `novo_str_byte_at` reaches `novo_some_int` reaches
# `novo_alloc_atomic`, and none of that is visible in the caller's IR.
BOXERS = ['novo_alloc', 'novo_some_int', 'novo_some_float',
          'novo_str_byte_at(', 'novo_bytes_byte_at(']

# `base64` is not matched: it allocates, that is what it is for.  The
# claim this package makes is about the half that runs on a device.
CORE = re.compile(r'^novo_user_base64_core_')

FNS = re.compile(r'^define[^\n]*?@([A-Za-z0-9_.]+)\([^\n]*\{\n(.*?)\n\}',
                 re.S | re.M)

# `base64_core` has fourteen `pub fn`s and the probe reaches every one.
# Fewer than this in the IR means the probe or the name scheme moved and
# the scan is measuring nothing.
FLOOR = 14


def main(path):
    src = open(path).read()
    seen, offenders = 0, []
    for m in FNS.finditer(src):
        name, body = m.group(1), m.group(2)
        if not CORE.match(name):
            continue
        seen += 1
        for boxer in BOXERS:
            if 'call' in body and ('@' + boxer) in body:
                offenders.append('%s: %s' % (name, boxer.rstrip('(')))
    if seen < FLOOR:
        print('FAIL only %d core function(s) in the IR, expected at least '
              '%d — the probe or the name scheme moved, and this check was '
              'measuring nothing' % (seen, FLOOR))
    elif offenders:
        print('FAIL ' + '; '.join(sorted(set(offenders))))
    else:
        print('OK %d function(s) in base64_core, zero heap cells' % seen)


if __name__ == '__main__':
    main(sys.argv[1])
