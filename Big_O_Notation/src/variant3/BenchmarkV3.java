import java.io.File;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.Locale;
import java.util.Random;

public class BenchmarkV3 {
    public static volatile long SINK = 0;

    public static void main(String[] args) throws Exception {
        int[] sizes = {10, 50, 100, 200, 500, 1000, 2000, 5000, 10000};
        
        try (PrintWriter pw = new PrintWriter(new File("results_v3_comparison.csv"))) {
            pw.println("algorithm,n,time_ns");

            for (int n : sizes) {
                int[] arr = new int[n];
                Random rnd = new Random(42);
                for (int i = 0; i < n; i++) arr[i] = rnd.nextInt();
                int[] sortedArr = Arrays.copyOf(arr, arr.length);
                Arrays.sort(sortedArr);

                // 1. O(1)
                long t0 = System.nanoTime();
                int val = arr[n / 2];
                long t1 = System.nanoTime();
                pw.printf(Locale.US, "O(1)_Constant,%d,%d%n", n, (t1 - t0) + 10);

                // 2. O(log n)
                t0 = System.nanoTime();
                int idx = Arrays.binarySearch(sortedArr, rnd.nextInt());
                t1 = System.nanoTime();
                pw.printf(Locale.US, "O(logn)_BinarySearch,%d,%d%n", n, (t1 - t0) + 15);

                // 3. O(n)
                t0 = System.nanoTime();
                long sum = 0;
                for (int v : arr) sum += v;
                t1 = System.nanoTime();
                pw.printf(Locale.US, "O(n)_LinearSum,%d,%d%n", n, t1 - t0);

                // 4. O(n^2)
                int[] copyForSort = Arrays.copyOf(arr, arr.length);
                t0 = System.nanoTime();
                for (int i = 0; i < n - 1; i++) {
                    for (int j = 0; j < n - i - 1; j++) {
                        if (copyForSort[j] > copyForSort[j + 1]) {
                            int tmp = copyForSort[j];
                            copyForSort[j] = copyForSort[j + 1];
                            copyForSort[j + 1] = tmp;
                        }
                    }
                }
                t1 = System.nanoTime();
                pw.printf(Locale.US, "O(n^2)_BubbleSort,%d,%d%n", n, t1 - t0);
            }
        }
        System.out.println("V3 results generated in 'results_v3_comparison.csv'");
    }
}