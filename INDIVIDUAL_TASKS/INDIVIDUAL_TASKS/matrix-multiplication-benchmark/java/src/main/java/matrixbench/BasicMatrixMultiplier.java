package matrixbench;

/**
 * Naive i-j-k triple-loop multiplication of two n x n matrices stored as double[][].
 * The result array is allocated inside multiply() (the JVM zero-initialises it).
 */
public final class BasicMatrixMultiplier {

    private BasicMatrixMultiplier() { }

    public static double[][] multiply(double[][] a, double[][] b) {
        int n = a.length;
        double[][] c = new double[n][n];
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                double sum = 0.0;
                for (int k = 0; k < n; k++) {
                    sum += a[i][k] * b[k][j];
                }
                c[i][j] = sum;
            }
        }
        return c;
    }

    /** Sum of all elements in row-major order. */
    public static double checksum(double[][] m) {
        double s = 0.0;
        for (double[] row : m) {
            for (double x : row) {
                s += x;
            }
        }
        return s;
    }
}
