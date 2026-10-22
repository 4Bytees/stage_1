import java.io.File;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.Locale;
import java.util.Random;

public class BenchmarkV2 {

    private static final long TIME_BUDGET_NS = 5_000_000_000L; // Budget: 5 seconds

    public static void main(String[] args) throws Exception {
        System.out.println("=== VARIANT 2: SCALING LIMITS (TIME BUDGET = 5s) ===");
        
        try (PrintWriter pw = new PrintWriter(new File("results_v2_limits.csv"))) {
            pw.println("algorithm,n,time_ms,exceeded_budget");

            // 1. O(2^n) - Recursive Fibonacci
            runExponentialLimit(pw);

            // 2. O(n^2) - Bubble Sort
            runQuadraticLimit(pw);

            // 3. O(n log n) - Arrays.sort
            runLinearithmicLimit(pw);

            // 4. O(n) - Linear Sum
            runLinearLimit(pw);
        }
        System.out.println("\nResults exported to 'results_v2_limits.csv'");
    }

    private static void runExponentialLimit(PrintWriter pw) {
        System.out.println("\n--- Testing O(2^n) Fibonacci ---");
        for (int n = 10; n <= 50; n++) {
            long t0 = System.nanoTime();
            long val = fibonacci(n);
            long elapsed = System.nanoTime() - t0;
            double ms = elapsed / 1_000_000.0;
            boolean exceeded = elapsed > TIME_BUDGET_NS;
            
            pw.printf(Locale.US, "O(2^n)_Fibonacci,%d,%.3f,%b%n", n, ms, exceeded);
            System.out.printf("n=%d | Time: %.3f ms | Limit exceeded: %b%n", n, ms, exceeded);
            
            if (exceeded) break;
        }
    }

    private static void runQuadraticLimit(PrintWriter pw) {
        System.out.println("\n--- Testing O(n^2) Bubble Sort ---");
        int[] sizes = {1000, 5000, 10000, 20000, 40000, 80000, 150000};
        for (int n : sizes) {
            int[] arr = generateRandomArray(n, 42);
            long t0 = System.nanoTime();
            bubbleSort(arr);
            long elapsed = System.nanoTime() - t0;
            double ms = elapsed / 1_000_000.0;
            boolean exceeded = elapsed > TIME_BUDGET_NS;

            pw.printf(Locale.US, "O(n^2)_BubbleSort,%d,%.3f,%b%n", n, ms, exceeded);
            System.out.printf("n=%d | Time: %.3f ms | Limit exceeded: %b%n", n, ms, exceeded);

            if (exceeded) break;
        }
    }

    private static void runLinearithmicLimit(PrintWriter pw) {
        System.out.println("\n--- Testing O(n log n) Dual-Pivot Quicksort ---");
        int n = 100_000;
        while (true) {
            try {
                int[] arr = generateRandomArray(n, 42);
                long t0 = System.nanoTime();
                Arrays.sort(arr);
                long elapsed = System.nanoTime() - t0;
                double ms = elapsed / 1_000_000.0;
                boolean exceeded = elapsed > TIME_BUDGET_NS;

                pw.printf(Locale.US, "O(nlogn)_QuickSort,%d,%.3f,%b%n", n, ms, exceeded);
                System.out.printf("n=%d | Time: %.3f ms | Limit exceeded: %b%n", n, ms, exceeded);

                if (exceeded || n >= 100_000_000) break;
                n = (int)(n * 1.8);
            } catch (OutOfMemoryError e) {
                System.out.println("Limit reached due to RAM (OutOfMemoryError) at n=" + n);
                break;
            }
        }
    }

    private static void runLinearLimit(PrintWriter pw) {
        System.out.println("\n--- Testing O(n) Scan ---");
        int n = 1_000_000;
        while (true) {
            try {
                int[] arr = generateRandomArray(n, 42);
                long t0 = System.nanoTime();
                long sum = 0;
                for (int v : arr) sum += v;
                long elapsed = System.nanoTime() - t0;
                double ms = elapsed / 1_000_000.0;
                boolean exceeded = elapsed > TIME_BUDGET_NS;

                pw.printf(Locale.US, "O(n)_LinearScan,%d,%.3f,%b%n", n, ms, exceeded);
                System.out.printf("n=%d | Time: %.3f ms | Limit exceeded: %b%n", n, ms, exceeded);

                if (exceeded || n >= 200_000_000) break;
                n = (int)(n * 1.8);
            } catch (OutOfMemoryError e) {
                System.out.println("Limit reached due to RAM (OutOfMemoryError) at n=" + n);
                break;
            }
        }
    }

    private static long fibonacci(int n) {
        if (n <= 1) return n;
        return fibonacci(n - 1) + fibonacci(n - 2);
    }

    private static void bubbleSort(int[] arr) {
        int len = arr.length;
        for (int i = 0; i < len - 1; i++) {
            for (int j = 0; j < len - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int tmp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = tmp;
                }
            }
        }
    }

    private static int[] generateRandomArray(int size, long seed) {
        int[] arr = new int[size];
        Random rnd = new Random(seed);
        for (int i = 0; i < size; i++) arr[i] = rnd.nextInt();
        return arr;
    }
}