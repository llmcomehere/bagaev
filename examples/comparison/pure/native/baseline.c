#include "checked.h"

/* One independently handwritten literal program per compilation. No default. */
#ifndef BAGAEV_NATIVE_CASE
#error "Select exactly one documented BAGAEV_NATIVE_CASE (1..23)."
#endif

#if BAGAEV_NATIVE_CASE == 1 /* K-MIN */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    (void)slots;
    BAGAEV_TICK(1);
    return INT64_MIN;
}
#elif BAGAEV_NATIVE_CASE == 2 /* K-MAX */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    (void)slots;
    BAGAEV_TICK(1);
    return INT64_MAX;
}
#elif BAGAEV_NATIVE_CASE == 3 /* K-ADD */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_C(2);
    BAGAEV_TICK(3); right = INT64_C(3);
    if (!bagaev_add(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 4 /* K-SUB */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_C(2);
    BAGAEV_TICK(3); right = INT64_C(3);
    if (!bagaev_sub(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 5 /* K-MUL */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = -INT64_C(3);
    BAGAEV_TICK(3); right = INT64_C(4);
    if (!bagaev_mul(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 6 /* K-EQ */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_C(1);
    BAGAEV_TICK(3); right = INT64_C(0);
    return left == right;
}
#elif BAGAEV_NATIVE_CASE == 7 /* K-LT */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_MIN;
    BAGAEV_TICK(3); right = INT64_MAX;
    return left < right;
}
#elif BAGAEV_NATIVE_CASE == 8 /* K-LE */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_C(2);
    BAGAEV_TICK(3); right = INT64_C(2);
    return left <= right;
}
#elif BAGAEV_NATIVE_CASE == 9 /* K-NOT */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t operand;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); operand = INT64_C(1);
    return !operand;
}
#elif BAGAEV_NATIVE_CASE == 10 /* K-LET */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t v;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); v = INT64_C(7);
    BAGAEV_TICK(3);
    return v;
}
#elif BAGAEV_NATIVE_CASE == 11 /* K-CALL: a before main in source numbering */
static int64_t native_a(BagaevWork *s, int64_t v)
{
    BAGAEV_TICK(1);
    return v;
}
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t argument;
    (void)slots;
    BAGAEV_TICK(2);
    BAGAEV_TICK(3); argument = INT64_C(9);
    return native_a(s, argument);
}
#elif BAGAEV_NATIVE_CASE == 12 /* K-LOOP-ZERO */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t accumulator;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); accumulator = INT64_C(8);
    for (int64_t i = INT64_C(0); i < INT64_C(0); ++i) {
        int64_t left, right, next;
        BAGAEV_TICK(3);
        BAGAEV_TICK(4); left = INT64_MAX;
        BAGAEV_TICK(5); right = INT64_C(1);
        if (!bagaev_add(s, UINT32_C(3), left, right, &next)) return INT64_C(0);
        accumulator = next;
    }
    return accumulator;
}
#elif BAGAEV_NATIVE_CASE == 13 /* K-LOOP-MAX */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t accumulator;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); accumulator = INT64_C(0);
    for (int64_t i = INT64_C(0); i < INT64_C(1024); ++i) {
        int64_t left, right, next;
        BAGAEV_TICK(3);
        BAGAEV_TICK(4); left = accumulator;
        BAGAEV_TICK(5); right = i;
        if (!bagaev_add(s, UINT32_C(3), left, right, &next)) return INT64_C(0);
        accumulator = next;
    }
    return accumulator;
}
#elif BAGAEV_NATIVE_CASE == 14 /* K-LAZY before */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t condition;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); condition = INT64_C(0);
    if (condition) {
        int64_t left, right, value;
        BAGAEV_TICK(3);
        BAGAEV_TICK(4); left = INT64_MAX;
        BAGAEV_TICK(5); right = INT64_C(1);
        if (!bagaev_add(s, UINT32_C(3), left, right, &value)) return INT64_C(0);
        return value;
    } else {
        BAGAEV_TICK(6);
        return INT64_C(4);
    }
}
#elif BAGAEV_NATIVE_CASE == 15 /* K-LAZY literal after[0] */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t condition;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); condition = INT64_C(1);
    if (condition) {
        BAGAEV_TICK(3);
        return INT64_C(0);
    } else {
        int64_t outer_accumulator;
        BAGAEV_TICK(4);
        BAGAEV_TICK(5); outer_accumulator = INT64_C(0);
        for (int64_t i = INT64_C(0); i < INT64_C(1024); ++i) {
            int64_t inner_accumulator;
            BAGAEV_TICK(6);
            BAGAEV_TICK(7); inner_accumulator = INT64_C(0);
            for (int64_t j = INT64_C(0); j < INT64_C(1024); ++j) {
                BAGAEV_TICK(8);
                inner_accumulator = INT64_C(0);
            }
            outer_accumulator = inner_accumulator;
        }
        return outer_accumulator;
    }
}
#elif BAGAEV_NATIVE_CASE == 16 /* K-OVER-ADD */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_MAX;
    BAGAEV_TICK(3); right = INT64_C(1);
    if (!bagaev_add(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 17 /* K-OVER-SUB */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_MIN;
    BAGAEV_TICK(3); right = INT64_C(1);
    if (!bagaev_sub(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 18 /* K-OVER-MUL */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); left = INT64_MIN;
    BAGAEV_TICK(3); right = -INT64_C(1);
    if (!bagaev_mul(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 19 /* K-LEFT-FAIL */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t left_a, left_b, left, right_a, right_b, right, value;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2);
    BAGAEV_TICK(3); left_a = INT64_MIN;
    BAGAEV_TICK(4); left_b = INT64_C(1);
    if (!bagaev_sub(s, UINT32_C(2), left_a, left_b, &left)) return INT64_C(0);
    BAGAEV_TICK(5);
    BAGAEV_TICK(6); right_a = INT64_MAX;
    BAGAEV_TICK(7); right_b = INT64_C(2);
    if (!bagaev_mul(s, UINT32_C(5), right_a, right_b, &right)) return INT64_C(0);
    if (!bagaev_add(s, UINT32_C(1), left, right, &value)) return INT64_C(0);
    return value;
}
#elif BAGAEV_NATIVE_CASE == 20 /* K-LOOP-FAIL */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t accumulator;
    (void)slots;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); accumulator = INT64_MAX;
    for (int64_t i = INT64_C(0); i < INT64_C(1024); ++i) {
        int64_t left, right, next;
        BAGAEV_TICK(3);
        BAGAEV_TICK(4); left = accumulator;
        BAGAEV_TICK(5); right = INT64_C(1);
        if (!bagaev_add(s, UINT32_C(3), left, right, &next)) return INT64_C(0);
        accumulator = next;
    }
    return accumulator;
}
#elif BAGAEV_NATIVE_CASE == 21 /* K-ABI-BOOL */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    BAGAEV_TICK(1);
    return slots[0];
}
#elif BAGAEV_NATIVE_CASE == 22 /* K-ABI-UNUSED */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    (void)slots;
    BAGAEV_TICK(1);
    return INT64_C(0);
}
#elif BAGAEV_NATIVE_CASE == 23 /* K-ABI-VALID */
static int64_t native_main(BagaevWork *s, const int64_t slots[8])
{
    int64_t condition;
    BAGAEV_TICK(1);
    BAGAEV_TICK(2); condition = slots[1];
    if (condition) {
        BAGAEV_TICK(3);
        return slots[0];
    } else {
        BAGAEV_TICK(4);
        return INT64_C(0);
    }
}
#else
#error "Unsupported BAGAEV_NATIVE_CASE: choose a documented integer 1..23."
#endif

#if BAGAEV_NATIVE_CASE == 21
#define BAGAEV_ACTIVE_SLOTS 1U
#define BAGAEV_BOOL_MASK 1U
#elif BAGAEV_NATIVE_CASE == 23
#define BAGAEV_ACTIVE_SLOTS 2U
#define BAGAEV_BOOL_MASK 2U
#else
#define BAGAEV_ACTIVE_SLOTS 0U
#define BAGAEV_BOOL_MASK 0U
#endif

#if (BAGAEV_NATIVE_CASE >= 6 && BAGAEV_NATIVE_CASE <= 9) || BAGAEV_NATIVE_CASE == 21
#define BAGAEV_RESULT_TYPE UINT32_C(2)
#else
#define BAGAEV_RESULT_TYPE UINT32_C(1)
#endif

void bagaev_probe_entry(const int64_t arguments[8], void *output)
{
    int64_t slots[8];
    BagaevWork state = {UINT64_C(0), UINT32_C(0), UINT32_C(0), UINT32_C(0)};
    int64_t value;

    /* Volatile-qualified reads keep even otherwise unused slots observable.
     * Read all eight first; never write either caller region during this pass. */
    for (unsigned int i = 0; i < 8; ++i)
        slots[i] = ((const volatile int64_t *)arguments)[i];

    for (unsigned int i = 0; i < 8; ++i) {
        int bad;
        if (i >= BAGAEV_ACTIVE_SLOTS)
            bad = slots[i] != INT64_C(0);
        else if ((BAGAEV_BOOL_MASK & (1U << i)) != 0U)
            bad = slots[i] != INT64_C(0) && slots[i] != INT64_C(1);
        else
            bad = 0;
        if (bad) {
            state.status = UINT32_C(3);
            state.reason = UINT32_C(8);
            state.location = UINT32_C(0x80000001) + (uint32_t)i;
            bagaev_output(output, &state, UINT32_C(0), INT64_C(0));
            return;
        }
    }
    value = native_main(&state, slots);
    bagaev_output(output, &state, BAGAEV_RESULT_TYPE, value);
}
