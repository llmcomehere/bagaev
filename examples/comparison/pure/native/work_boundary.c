#include "checked.h"

/* One fixed literal program per compilation; no implicit selection. */
#ifndef BAGAEV_WORK_COUNT
#error "Define BAGAEV_WORK_COUNT as exactly 1019 or 1020."
#elif BAGAEV_WORK_COUNT != 1019 && BAGAEV_WORK_COUNT != 1020
#error "BAGAEV_WORK_COUNT must be exactly 1019 or 1020."
#endif

/* Node numbers are complete source preorder; see WORK_BOUNDARY.md. */
static int64_t work_boundary_main(BagaevWork *s)
{
    int64_t a;

    BAGAEV_TICK(1); /* let v: tick before its value. */
    BAGAEV_TICK(2); /* outer loop: initial once, body per iteration. */
    BAGAEV_TICK(3); a = INT64_C(0);
    for (int64_t i = INT64_C(0); i < INT64_C(1024); ++i) {
        int64_t b;

        BAGAEV_TICK(4); /* inner loop expression for this outer body. */
        BAGAEV_TICK(5); b = INT64_C(0);
        for (int64_t j = INT64_C(0); j < INT64_C(61); ++j) {
            int64_t next;

            BAGAEV_TICK(6); next = INT64_C(0);
            b = next;
        }
        a = b;
    }

    /* v is bound only after the entire let value has succeeded. */
    {
        const int64_t v = a;
        int64_t c;

        (void)v; /* The fixed let body does not use this binding. */
        BAGAEV_TICK(7); /* let body: the second loop. */
        BAGAEV_TICK(8); c = INT64_C(0);
        for (int64_t k = INT64_C(0); k < BAGAEV_WORK_COUNT; ++k) {
            int64_t next;

            BAGAEV_TICK(9); next = c;
            c = next;
        }
        return c;
    }
}

void bagaev_probe_entry(const int64_t arguments[8], void *output)
{
    int64_t slots[8];
    const volatile int64_t *input = (const volatile int64_t *)arguments;
    BagaevWork state = {UINT64_C(0), UINT32_C(0), UINT32_C(0), UINT32_C(0)};
    int64_t value;

    /* Consume every caller-owned slot before validation can write output. */
    for (unsigned int i = 0; i < 8; ++i)
        slots[i] = input[i];

    /* params[]: all eight slots are unused, validated in increasing order. */
    for (unsigned int i = 0; i < 8; ++i) {
        if (slots[i] != INT64_C(0)) {
            state.status = UINT32_C(3);
            state.reason = UINT32_C(8);
            state.location = UINT32_C(0x80000001) + (uint32_t)i;
            bagaev_output(output, &state, UINT32_C(1), INT64_C(0));
            return;
        }
    }

    value = work_boundary_main(&state);
    bagaev_output(output, &state, UINT32_C(1), value);
}
