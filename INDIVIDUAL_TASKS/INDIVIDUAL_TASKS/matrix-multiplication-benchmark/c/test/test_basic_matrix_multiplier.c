#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../src/basic_matrix_multiplier.h"

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } else { printf("ok:   %s\n", msg); } } while (0)

static void test_known_2x2(void) {
    double A[] = {1, 2, 3, 4}, B[] = {5, 6, 7, 8};
    double *C = multiply(A, B, 2);
    CHECK(C[0] == 19 && C[1] == 22 && C[2] == 43 && C[3] == 50, "2x2 known answer");
    free(C);
}

static void test_1x1(void) {
    double A[] = {3.5}, B[] = {2.0};
    double *C = multiply(A, B, 1);
    CHECK(C[0] == 7.0, "1x1");
    free(C);
}

static void test_identity_and_zero(void) {
    int n = 17;
    size_t N = (size_t)n;
    double *A = malloc(N * N * sizeof(double));
    double *I = calloc(N * N, sizeof(double));
    double *Z = calloc(N * N, sizeof(double));
    for (size_t i = 0; i < N; ++i) {
        I[i * N + i] = 1.0;
        for (size_t j = 0; j < N; ++j) A[i * N + j] = (double)((i * 7 + j * 3) % 11) - 5.0;
    }
    double *AI = multiply(A, I, n);
    double *IA = multiply(I, A, n);
    double *AZ = multiply(A, Z, n);
    CHECK(memcmp(AI, A, N * N * sizeof(double)) == 0, "A * I == A");
    CHECK(memcmp(IA, A, N * N * sizeof(double)) == 0, "I * A == A");
    CHECK(memcmp(AZ, Z, N * N * sizeof(double)) == 0, "A * 0 == 0");
    free(A); free(I); free(Z); free(AI); free(IA); free(AZ);
}

static void test_non_commutative(void) {
    double A[] = {1, 2, 3, 4}, B[] = {0, 1, 1, 0};
    double *AB = multiply(A, B, 2), *BA = multiply(B, A, 2);
    CHECK(AB[0] == 2 && AB[1] == 1 && AB[2] == 4 && AB[3] == 3, "A*B (column swap)");
    CHECK(BA[0] == 3 && BA[1] == 4 && BA[2] == 1 && BA[3] == 2, "B*A (row swap)");
    free(AB); free(BA);
}

int main(void) {
    test_known_2x2();
    test_1x1();
    test_identity_and_zero();
    test_non_commutative();
    printf(failures ? "\n%d test(s) FAILED\n" : "\nAll C tests passed\n", failures);
    return failures ? 1 : 0;
}
