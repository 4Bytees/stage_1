import java.io.File;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.Locale;
import java.util.Random;

public class BenchmarkV1 {

    public static volatile long BLACKHOLE = 0;

    interface AlgorithmTask {
        String getId();
        void prepare(int n);
        long execute();
    }

    // O(1) - Constant-position memory access
    static final class ConstantAccessTask implements AlgorithmTask {
        private int[] data;
        
        public String getId() { return "O1_ConstantAccess"; }
        
        public void prepare(int n) {
            data = generateRandomArray(Math.max(2048, n), 101);
        }
        
        public long execute() {
            long accum = 0;
            int mask = data.length - 1;
            int iterations = 1_000_000;
            for (int i = 0; i < iterations; i++) {
                accum += data[(i * 31 + 7) & mask];
            }
            return accum;
        }
    }

    // O(n) - Linear traversal and accumulation
    static final class LinearScanTask implements AlgorithmTask {
        private int[] data;
        
        public String getId() { return "On_LinearScan"; }
        
        public void prepare(int n) {
            data = generateRandomArray(n, 202);
        }
        
        public long execute() {
            long sum = 0;
            int repeats = 200; // Amplifies the signal so it can be measured cleanly
            for (int r = 0; r < repeats; r++) {
                for (int i = 0; i < data.length; i++) {
                    sum += data[i];
                }
            }
            return sum;
        }
    }

    // O(n log n) - Array sorting
    static final class LinearithmicSortTask implements AlgorithmTask {
        private int[] originalData;
        
        public String getId() { return "OnLogn_ArraySort"; }
        
        public void prepare(int n) {
            originalData = generateRandomArray(n, 303);
        }
        
        public long execute() {
            int[] copy = Arrays.copyOf(originalData, originalData.length);
            Arrays.sort(copy);
            return copy[0] ^ copy[copy.length - 1];
        }
    }

    public static void main(String[] args) throws Exception {
        AlgorithmTask[] tasks = {
            new ConstantAccessTask(),
            new LinearScanTask(),
            new LinearithmicSortTask()
        };

        int[] inputSizes = {2000, 4000, 8000, 16000, 32000, 64000, 128000, 256000};
        final int WARMUP_RUNS = 8;
        final int MEASURE_RUNS = 25;

        try (PrintWriter writer = new PrintWriter(new File("results_v1.csv"))) {
            writer.println("algorithm,n,iteration,time_ns,time_ms");
            
            for (AlgorithmTask task : tasks) {
                System.out.println("Running: " + task.getId());
                for (int n : inputSizes) {
                    task.prepare(n);
                    
                    // JIT warm-up
                    for (int w = 0; w < WARMUP_RUNS; w++) {
                        BLACKHOLE ^= task.execute();
                    }
                    
                    // Measurement
                    for (int r = 0; r < MEASURE_RUNS; r++) {
                        long start = System.nanoTime();
                        long result = task.execute();
                        long elapsedNs = System.nanoTime() - start;
                        BLACKHOLE ^= result;
                        
                        // Explicit use of Locale.US to force the decimal point
                        writer.printf(Locale.US, "%s,%d,%d,%d,%.4f%n", 
                                task.getId(), n, r, elapsedNs, elapsedNs / 1_000_000.0);
                    }
                }
            }
        }
        System.out.println("Results saved successfully to results_v1.csv");
    }

    private static int[] generateRandomArray(int size, long seed) {
        int[] arr = new int[size];
        Random prng = new Random(seed);
        for (int i = 0; i < size; i++) {
            arr[i] = prng.nextInt();
        }
        return arr;
    }
}