#ifndef BAGAEV_NATIVE_ABI_H
#define BAGAEV_NATIVE_ABI_H

#include <limits.h>
#include <stdint.h>

#if !defined(__x86_64__) || !defined(__linux__)
#error "This experimental ABI requires x86_64 Linux."
#endif
_Static_assert(CHAR_BIT == 8, "Eight-bit bytes required");
_Static_assert(sizeof(int64_t) == 8 && sizeof(uint64_t) == 8,
               "Exact 64-bit scalar types required");
_Static_assert(sizeof(uint32_t) == 4, "Exact 32-bit fields required");
_Static_assert(INT64_MIN == (-INT64_MAX - INT64_C(1)),
               "Two's complement Int64 required");

/* Non-null, eight-byte-aligned, valid disjoint 64/32-byte regions required.
 * The entry retains neither pointer. Byte layout is not a C struct layout. */
void bagaev_probe_entry(const int64_t arguments[8], void *output);

#endif
