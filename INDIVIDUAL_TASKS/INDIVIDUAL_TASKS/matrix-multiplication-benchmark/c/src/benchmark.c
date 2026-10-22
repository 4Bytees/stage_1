
#include <stdio.h>
#include <stdlib.h>
#include "basic_matrix_multiplier.h"

#ifdef _WIN32
#include <windows.h>
static double now_seconds(void) {
    LARGE_INTEGER t, f;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart / (double)f.QuadPart;
}
#else
#include <time.h>
static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}
#endif

static double *read_matrix(const char *dir, const char *name, int n) {
    char path[1024];
    snprintf(path, sizeof(path), "%s/%s_%d.bin", dir, name, n);
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(2); }
    size_t count = (size_t)n * (size_t)n;
    double *m = (double *)malloc(count * sizeof(double));
    if (!m) { fprintf(stderr, "out of memory\n"); exit(3); }
    if (fread(m, sizeof(double), count, f) != count) {
        fprintf(stderr, "short read on %s\n", path);
        exit(2);
    }
    fclose(f);
    return m;
}

/* Deterministic small matrices for warm-up (same formula in all languages). */
#define WARMUP_N 128
static void warmup_matrix(double *m, int n, int salt) {
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            m[(size_t)i * n + j] = (double)((i * 31 + j * 17 + salt) % 100) / 100.0;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <input_dir> <n> <warmup> [dump_file]\n", argv[0]);
        return 1;
    }
    const char *dir = argv[1];
    int n = atoi(argv[2]);
    int warmup = atoi(argv[3]);
    const char *dump = argc > 4 ? argv[4] : NULL;

    double *A = read_matrix(dir, "A", n);
    double *B = read_matrix(dir, "B", n);

    double sink = 0.0;
    if (warmup > 0) {
        double *wa = (double *)malloc(sizeof(double) * WARMUP_N * WARMUP_N);
        double *wb = (double *)malloc(sizeof(double) * WARMUP_N * WARMUP_N);
        warmup_matrix(wa, WARMUP_N, 1);
        warmup_matrix(wb, WARMUP_N, 7);
        for (int w = 0; w < warmup; ++w) {
            double *wc = multiply(wa, wb, WARMUP_N);
            sink += checksum(wc, WARMUP_N);
            free(wc);
        }
        free(wa); free(wb);
    }

    double t0 = now_seconds();
    double *C = multiply(A, B, n);
    double t1 = now_seconds();
    if (!C) { fprintf(stderr, "allocation of result failed\n"); return 3; }

    double cs = checksum(C, n);
    if (dump) {
        FILE *f = fopen(dump, "wb");
        if (!f) { fprintf(stderr, "cannot open dump file\n"); return 2; }
        fwrite(C, sizeof(double), (size_t)n * (size_t)n, f);
        fclose(f);
    }
    printf("RESULT time_s=%.9f checksum=%.17g\n", t1 - t0, cs);
    if (sink < 0) fprintf(stderr, "%g\n", sink); /* keeps warm-up result observable */

    free(A); free(B); free(C);
    return 0;
}
