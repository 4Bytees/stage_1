package matrixbench;

import java.util.Arrays;

public final class BasicMatrixMultiplierTest {

    private static int failures = 0;

    private static void check(boolean cond, String msg) {
        System.out.println((cond ? "ok:   " : "FAIL: ") + msg);
        if (!cond) failures++;
    }

    private static boolean equal(double[][] x, double[][] y) {
        return Arrays.deepEquals(x, y);
    }

    public static void main(String[] args) {
        double[][] c = BasicMatrixMultiplier.multiply(
                new double[][]{{1, 2}, {3, 4}}, new double[][]{{5, 6}, {7, 8}});
        check(equal(c, new double[][]{{19, 22}, {43, 50}}), "2x2 known answer");

        c = BasicMatrixMultiplier.multiply(new double[][]{{3.5}}, new double[][]{{2.0}});
        check(c[0][0] == 7.0, "1x1");

        int n = 17;
        double[][] a = new double[n][n], id = new double[n][n], z = new double[n][n];
        for (int i = 0; i < n; i++) {
            id[i][i] = 1.0;
            for (int j = 0; j < n; j++) a[i][j] = ((i * 7 + j * 3) % 11) - 5.0;
        }
        check(equal(BasicMatrixMultiplier.multiply(a, id), a), "A * I == A");
        check(equal(BasicMatrixMultiplier.multiply(id, a), a), "I * A == A");
        check(equal(BasicMatrixMultiplier.multiply(a, z), z), "A * 0 == 0");

        double[][] p = {{1, 2}, {3, 4}}, swap = {{0, 1}, {1, 0}};
        check(equal(BasicMatrixMultiplier.multiply(p, swap), new double[][]{{2, 1}, {4, 3}}), "A*B (column swap)");
        check(equal(BasicMatrixMultiplier.multiply(swap, p), new double[][]{{3, 4}, {1, 2}}), "B*A (row swap)");

        System.out.println(failures == 0 ? "\nAll Java tests passed" : "\n" + failures + " test(s) FAILED");
        System.exit(failures == 0 ? 0 : 1);
    }
}
