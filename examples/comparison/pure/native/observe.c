#include "abi.h"
#include <stdio.h>
#include <string.h>

/* Raw direct-ABI observer: no parser, evaluator or expected-value checker. */
static int environment_failure(const char *message)
{
    (void)fprintf(stderr, "ABI observer: %s\n", message);
    return 1;
}

static int64_t decode_slot(const unsigned char *bytes)
{
    uint64_t bits = UINT64_C(0);
    for (unsigned int i = 0; i < 8; ++i)
        bits |= (uint64_t)bytes[i] << (8U * i);
    if (bits <= (uint64_t)INT64_MAX)
        return (int64_t)bits;
    /* Both the conversion and addition stay within signed Int64 range. */
    return INT64_MIN + (int64_t)(bits - (UINT64_C(1) << 63));
}

static void encode_slot(unsigned char *bytes, int64_t value)
{
    uint64_t bits = (uint64_t)value;
    for (unsigned int i = 0; i < 8; ++i)
        bytes[i] = (unsigned char)(bits >> (8U * i));
}

static void hex_bytes(char *text, const unsigned char *bytes, unsigned int count)
{
    static const char alphabet[] = "0123456789abcdef";
    for (unsigned int i = 0; i < count; ++i) {
        text[2U * i] = alphabet[bytes[i] >> 4];
        text[2U * i + 1U] = alphabet[bytes[i] & 15U];
    }
    text[2U * count] = '\0';
}

int main(int argc, char **argv)
{
    unsigned char before[64], after[64], prefill[32];
    _Alignas(8) int64_t arguments[8];
    _Alignas(8) unsigned char output[32];
    char before_hex[129], after_hex[129], prefill_hex[65], output_hex[65];
    char observation[640];
    unsigned char fill;
    FILE *input;
    size_t got;
    int extra, failed, written;

    if (argc != 5 || strcmp(argv[1], "--input") != 0 || argv[2][0] == '\0' ||
        strcmp(argv[3], "--prefill") != 0)
        return environment_failure("require --input PATH --prefill 00|ff");
    if (strcmp(argv[4], "00") == 0)
        fill = 0;
    else if (strcmp(argv[4], "ff") == 0)
        fill = 255;
    else
        return environment_failure("prefill must be exactly 00 or ff");

    input = fopen(argv[2], "rb");
    if (input == NULL)
        return environment_failure("input cannot be opened readonly");
    got = fread(before, 1, sizeof before, input);
    extra = fgetc(input);
    failed = ferror(input);
    if (fclose(input) != 0)
        failed = 1;
    if (failed || got != sizeof before || extra != EOF)
        return environment_failure("input must be exactly 64 complete bytes");

    for (unsigned int i = 0; i < 8; ++i)
        arguments[i] = decode_slot(before + 8U * i);
    for (unsigned int i = 0; i < 32; ++i) {
        prefill[i] = fill;
        output[i] = fill;
    }
    bagaev_probe_entry(arguments, output);
    for (unsigned int i = 0; i < 8; ++i)
        encode_slot(after + 8U * i, ((const volatile int64_t *)arguments)[i]);
    hex_bytes(before_hex, before, 64);
    hex_bytes(after_hex, after, 64);
    hex_bytes(prefill_hex, prefill, 32);
    hex_bytes(output_hex, output, 32);

    written = snprintf(observation, sizeof observation,
        "{\"schema\":\"bagaev-direct-abi-observation/1\","
        "\"input_before_hex\":\"%s\",\"input_after_hex\":\"%s\","
        "\"prefill_hex\":\"%s\",\"output_hex\":\"%s\"}\n",
        before_hex, after_hex, prefill_hex, output_hex);
    if (written < 0 || (size_t)written >= sizeof observation)
        return environment_failure("observation cannot be completed");
    if (fwrite(observation, 1, (size_t)written, stdout) != (size_t)written ||
        fflush(stdout) != 0)
        return environment_failure("observation cannot be emitted completely");
    return 0;
}
