#ifndef BAGAEV_NATIVE_CHECKED_H
#define BAGAEV_NATIVE_CHECKED_H

#include "abi.h"

#ifndef __clang__
#error "This C11 experiment explicitly requires Clang checked arithmetic."
#endif
#ifndef __has_builtin
#error "Checked arithmetic feature detection required."
#else
#if !__has_builtin(__builtin_add_overflow) || \
    !__has_builtin(__builtin_sub_overflow) || \
    !__has_builtin(__builtin_mul_overflow)
#error "All three checked arithmetic builtins are required."
#endif
#endif

typedef struct {
    volatile uint64_t work;
    uint32_t status;
    uint32_t reason;
    uint32_t location;
} BagaevWork;

static inline int bagaev_tick(BagaevWork *s, uint32_t node)
{
    if (s->work == UINT64_C(65536)) {
        s->status = UINT32_C(2);
        s->reason = UINT32_C(10);
        s->location = node;
        return 0;
    }
    s->work += UINT64_C(1);
    return 1;
}

static inline int bagaev_overflow(BagaevWork *s, uint32_t node)
{
    s->status = UINT32_C(1);
    s->reason = UINT32_C(9);
    s->location = node;
    return 0;
}

static inline int bagaev_add(BagaevWork *s, uint32_t node,
                            int64_t left, int64_t right, int64_t *value)
{
    if (__builtin_add_overflow(left, right, value))
        return bagaev_overflow(s, node);
    return 1;
}

static inline int bagaev_sub(BagaevWork *s, uint32_t node,
                            int64_t left, int64_t right, int64_t *value)
{
    if (__builtin_sub_overflow(left, right, value))
        return bagaev_overflow(s, node);
    return 1;
}

static inline int bagaev_mul(BagaevWork *s, uint32_t node,
                            int64_t left, int64_t right, int64_t *value)
{
    if (__builtin_mul_overflow(left, right, value))
        return bagaev_overflow(s, node);
    return 1;
}

static inline void bagaev_put32(unsigned char *p, uint32_t value)
{
    for (unsigned int i = 0; i < 4; ++i)
        p[i] = (unsigned char)(value >> (8U * i));
}

static inline void bagaev_put64(unsigned char *p, uint64_t value)
{
    for (unsigned int i = 0; i < 8; ++i)
        p[i] = (unsigned char)(value >> (8U * i));
}

static inline void bagaev_output(void *output, const BagaevWork *s,
                                 uint32_t value_type, int64_t value)
{
    unsigned char *p = (unsigned char *)output;
    bagaev_put32(p, s->status);
    bagaev_put32(p + 4, s->status == 0 ? value_type : UINT32_C(0));
    bagaev_put64(p + 8, s->status == 0 ? (uint64_t)value : UINT64_C(0));
    bagaev_put64(p + 16, s->work);
    bagaev_put32(p + 24, s->reason);
    bagaev_put32(p + 28, s->location);
}

/* Explicit, sequenced statement at each handwritten source expression. */
#define BAGAEV_TICK(node) do { \
    if (!bagaev_tick(s, UINT32_C(node))) return INT64_C(0); \
} while (0)

#endif
