#ifndef BASIC_MATRIX_MULTIPLIER_H
#define BASIC_MATRIX_MULTIPLIER_H

#include <stddef.h>

/*
 * Naive i-j-k triple-loop multiplication of two n x n matrices.
 * Matrices are stored contiguously in row-major order: element (i, j) is at index i * n + j.
 *
 * multiply() allocates the result with malloc and returns it (NULL on failure).
 * The caller must free() it. Every element of the result is written exactly once,
 * so the buffer is not zero-initialised separately.
 */
double *multiply(const double *A, const double *B, int n);

/* Sum of all elements in row-major order; used as a cheap correctness checksum. */
double checksum(const double *M, int n);

#endif
