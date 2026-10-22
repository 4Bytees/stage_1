package matrixbench;

import java.io.EOFException;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;


public final class Benchmark {

    private static final int WARMUP_N = 128;
    private static volatile double sink;

    private static double[][] readMatrix(Path path, int n) throws IOException {
        double[][] m = new double[n][n];
        try (FileChannel ch = FileChannel.open(path, StandardOpenOption.READ)) {
            ByteBuffer buf = ByteBuffer.allocate(n * 8).order(ByteOrder.LITTLE_ENDIAN);
            for (int i = 0; i < n; i++) {
                buf.clear();
                while (buf.hasRemaining()) {
                    if (ch.read(buf) < 0) throw new EOFException("short read on " + path);
                }
                buf.flip();
                buf.asDoubleBuffer().get(m[i]);
            }
        }
        return m;
    }

    private static double[][] warmupMatrix(int n, int salt) {
        double[][] m = new double[n][n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                m[i][j] = ((i * 31 + j * 17 + salt) % 100) / 100.0;
        return m;
    }

    private static void dump(double[][] c, Path path) throws IOException {
        int n = c.length;
        try (FileChannel ch = FileChannel.open(path, StandardOpenOption.WRITE,
                StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
            ByteBuffer buf = ByteBuffer.allocate(n * 8).order(ByteOrder.LITTLE_ENDIAN);
            for (int i = 0; i < n; i++) {
                buf.clear();
                buf.asDoubleBuffer().put(c[i]);
                buf.position(0).limit(n * 8);
                while (buf.hasRemaining()) ch.write(buf);
            }
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 3) {
            System.err.println("usage: Benchmark <input_dir> <n> <warmup> [dump_file]");
            System.exit(1);
        }
        Path dir = Paths.get(args[0]);
        int n = Integer.parseInt(args[1]);
        int warmup = Integer.parseInt(args[2]);

        double[][] a = readMatrix(dir.resolve("A_" + n + ".bin"), n);
        double[][] b = readMatrix(dir.resolve("B_" + n + ".bin"), n);

        if (warmup > 0) {
            double[][] wa = warmupMatrix(WARMUP_N, 1);
            double[][] wb = warmupMatrix(WARMUP_N, 7);
            double acc = 0.0;
            for (int w = 0; w < warmup; w++) {
                acc += BasicMatrixMultiplier.checksum(BasicMatrixMultiplier.multiply(wa, wb));
            }
            sink = acc;
        }

        long t0 = System.nanoTime();
        double[][] c = BasicMatrixMultiplier.multiply(a, b);
        long t1 = System.nanoTime();

        double cs = BasicMatrixMultiplier.checksum(c);
        if (args.length > 3) dump(c, Paths.get(args[3]));
        System.out.println(String.format(java.util.Locale.ROOT,
                "RESULT time_s=%.9f checksum=%.17g", (t1 - t0) / 1e9, cs));
    }
}
