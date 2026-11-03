import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public class QueryBenchmark {

    private static final Set<String> RESERVED_NAMES = Set.of(
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
            "LPT6", "LPT7", "LPT8", "LPT9"
    );

    public static class Posting {
        public final int bookId;
        public final int frequency;
        public final List<Integer> positions;

        public Posting(
                int bookId,
                int frequency,
                List<Integer> positions
        ) {
            this.bookId = bookId;
            this.frequency = frequency;
            this.positions = positions;
        }
    }

    public static List<Posting> queryHierarchical(
            Path datamarts,
            String rawTerm
    ) throws Exception {
        String term = rawTerm.toLowerCase(Locale.ROOT);

        if (!term.matches("[a-z]{3,}")) {
            throw new IllegalArgumentException(
                    "La consulta debe contener al menos tres letras ASCII."
            );
        }

        Path folder = datamarts.resolve("inverted_index_folders_java");

        if (!Files.isDirectory(folder)) {
            throw new IllegalStateException(
                    "No existe el indice jerarquico: " + folder
            );
        }

        String filename = RESERVED_NAMES.contains(
                term.toUpperCase(Locale.ROOT)
        ) ? "__term_" + term + ".txt" : term + ".txt";

        Path target = folder
                .resolve(term.substring(0, 1).toUpperCase(Locale.ROOT))
                .resolve(filename);

        List<Posting> postings = new ArrayList<>();

        if (!Files.exists(target)) {
            return postings;
        }

        Set<Integer> seenBooks = new HashSet<>();
        int lineNumber = 0;

        for (String rawLine : Files.readAllLines(
                target, StandardCharsets.UTF_8
        )) {
            lineNumber++;
            String line = rawLine.trim();

            if (line.isEmpty()) {
                continue;
            }

            try {
                String[] fields = line.split(",", 3);

                if (fields.length != 3) {
                    throw new IllegalArgumentException(
                            "Se esperan ID, frecuencia y posiciones."
                    );
                }

                int bookId = Integer.parseInt(fields[0].trim());
                int frequency = Integer.parseInt(fields[1].trim());
                String rawPositions = fields[2].trim();

                if (!rawPositions.startsWith("[")
                        || !rawPositions.endsWith("]")) {
                    throw new IllegalArgumentException(
                            "Lista de posiciones invalida."
                    );
                }

                String inner = rawPositions.substring(
                        1, rawPositions.length() - 1
                ).trim();

                List<Integer> positions = new ArrayList<>();
                int previous = -1;

                if (!inner.isEmpty()) {
                    for (String value : inner.split(",", -1)) {
                        int position = Integer.parseInt(value.trim());

                        if (position < 0 || position <= previous) {
                            throw new IllegalArgumentException(
                                    "Posiciones no crecientes o negativas."
                            );
                        }

                        positions.add(position);
                        previous = position;
                    }
                }

                if (bookId < 0 || frequency != positions.size()) {
                    throw new IllegalArgumentException(
                            "ID o frecuencia invalidos."
                    );
                }

                if (!seenBooks.add(bookId)) {
                    throw new IllegalArgumentException(
                            "Libro duplicado: " + bookId
                    );
                }

                postings.add(new Posting(
                        bookId, frequency, positions
                ));

            } catch (IllegalArgumentException error) {
                throw new IllegalArgumentException(
                        target + ", linea " + lineNumber
                                + ": " + error.getMessage(),
                        error
                );
            }
        }

        postings.sort(Comparator.comparingInt(posting -> posting.bookId));
        return postings;
    }

    private static double median(double[] values) {
        java.util.Arrays.sort(values);
        int middle = values.length / 2;

        return values.length % 2 == 0
                ? (values[middle - 1] + values[middle]) / 2.0
                : values[middle];
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            throw new IllegalArgumentException(
                    "Uso: QueryBenchmark <datamarts> <termino>..."
            );
        }

        Path datamarts = Paths.get(args[0]);
        StringBuilder output = new StringBuilder("{");
        int repeats = 10;
        int warmups = 2;

        for (int index = 1; index < args.length; index++) {
            String term = args[index].toLowerCase(Locale.ROOT);

            for (int warmup = 0; warmup < warmups; warmup++) {
                queryHierarchical(datamarts, term);
            }

            double[] samples = new double[repeats];
            List<Posting> postings = new ArrayList<>();

            for (int repeat = 0; repeat < repeats; repeat++) {
                long start = System.nanoTime();
                postings = queryHierarchical(datamarts, term);
                samples[repeat] =
                        (System.nanoTime() - start) / 1_000_000.0;
            }

            if (index > 1) {
                output.append(",");
            }

            output.append("\"").append(term).append("\":{")
                    .append("\"java_postings_count\":")
                    .append(postings.size())
                    .append(",\"java_query_ms\":")
                    .append(median(samples))
                    .append(",\"postings\":[");

            for (int p = 0; p < postings.size(); p++) {
                Posting posting = postings.get(p);

                if (p > 0) {
                    output.append(",");
                }

                output.append("{\"book_id\":")
                        .append(posting.bookId)
                        .append(",\"frequency\":")
                        .append(posting.frequency)
                        .append(",\"positions\":")
                        .append(posting.positions)
                        .append("}");
            }

            output.append("]}");
        }

        output.append("}");
        System.out.println(output);
    }
}