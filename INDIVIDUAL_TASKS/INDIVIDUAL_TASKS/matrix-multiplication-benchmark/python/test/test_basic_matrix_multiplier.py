import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from basic_matrix_multiplier import multiply  # noqa: E402


class TestBasicMatrixMultiplier(unittest.TestCase):
    def test_known_2x2(self):
        self.assertEqual(multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]), [[19, 22], [43, 50]])

    def test_1x1(self):
        self.assertEqual(multiply([[3.5]], [[2.0]]), [[7.0]])

    def test_identity_and_zero(self):
        n = 17
        a = [[float((i * 7 + j * 3) % 11 - 5) for j in range(n)] for i in range(n)]
        ident = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        zero = [[0.0] * n for _ in range(n)]
        self.assertEqual(multiply(a, ident), a)
        self.assertEqual(multiply(ident, a), a)
        self.assertEqual(multiply(a, zero), zero)

    def test_non_commutative(self):
        a, swap = [[1, 2], [3, 4]], [[0, 1], [1, 0]]
        self.assertEqual(multiply(a, swap), [[2, 1], [4, 3]])
        self.assertEqual(multiply(swap, a), [[3, 4], [1, 2]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
