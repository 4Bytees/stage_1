#include "basic_matrix_multiplier.h"
#include <stdlib.h>

double *multiply(const double *A, const double *B, int n) {
    size_t N = (size_t)n;
    double *C = (double *)malloc(N * N * sizeof(double));
    if (C == NULL) return NULL;

    for (size_t i = 0; i < N; ++i) {
        for (size_t j = 0; j < N; ++j) {
            double sum = 0.0;
            for (size_t k = 0; k < N; ++k) {
                sum += A[i * N + k] * B[k * N + j];
            }
            C[i * N + j] = sum;
        }
    }
    return C;
}

double checksum(const double *M, int n) {
    double s = 0.0;
    size_t total = (size_t)n * (size_t)n;
    for (size_t i = 0; i < total; ++i) s += M[i];
    return s;
}
