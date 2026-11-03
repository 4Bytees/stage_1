package indexer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class MonolithicIndexer extends BaseContainer {

    private final Path outputPath;

    public MonolithicIndexer() {
        this(DATAMARTS_DIR.resolve("inverted_index_java.json"));
    }

    public MonolithicIndexer(Path outputPath) {
        this.outputPath = outputPath;
    }

    /*
     * Parser del formato generado por este indexador:
     * termino -> ID -> {frequency, positions}.
     *
     * Rechaza formatos inesperados en lugar de empezar desde cero.
     */
    private static class Parser {
        private final String text;
        private int cursor = 0;

        Parser(String text) {
            this.text = text;
        }

        private void whitespace() {
            while (cursor < text.length()) {
                char c = text.charAt(cursor);

                if (c != ' ' && c != '\n' && c != '\r' && c != '\t') {
                    break;
                }

                cursor++;
            }
        }

        private boolean take(char expected) {
            whitespace();

            if (cursor < text.length()
                    && text.charAt(cursor) == expected) {
                cursor++;
                return true;
            }

            return false;
        }

        private void expect(char expected) {
            if (!take(expected)) {
                throw new IllegalArgumentException(
                        "JSON invalido en posicion " + cursor
                                + ": se esperaba " + expected
                );
            }
        }

        private String string() {
            expect('"');
            int start = cursor;

            while (cursor < text.length()
                    && text.charAt(cursor) != '"') {
                char c = text.charAt(cursor);

                if (c == '\\' || c < 32) {
                    throw new IllegalArgumentException(
                            "Cadena no admitida en el indice."
                    );
                }

                cursor++;
            }

            if (cursor >= text.length()) {
                throw new IllegalArgumentException("Cadena sin cerrar.");
            }

            String value = text.substring(start, cursor);
            cursor++;
            return value;
        }

        private int number() {
            whitespace();
            int start = cursor;

            while (cursor < text.length()
                    && text.charAt(cursor) >= '0'
                    && text.charAt(cursor) <= '9') {
                cursor++;
            }

            if (start == cursor) {
                throw new IllegalArgumentException(
                        "Se esperaba un entero no negativo."
                );
            }

            if (cursor - start > 1 && text.charAt(start) == '0') {
                throw new IllegalArgumentException(
                        "Entero JSON con cero inicial."
                );
            }

            return Integer.parseInt(text.substring(start, cursor));
        }

        private List<Integer> positions() {
            expect('[');
            List<Integer> result = new ArrayList<>();

            if (!take(']')) {
                do {
                    int position = number();

                    if (!result.isEmpty()
                            && position <= result.get(result.size() - 1)) {
                        throw new IllegalArgumentException(
                                "Posiciones no crecientes."
                        );
                    }

                    result.add(position);
                } while (take(','));

                expect(']');
            }

            return result;
        }

        private List<Integer> posting() {
            expect('{');

            Integer frequency = null;
            List<Integer> positions = null;

            do {
                String key = string();
                expect(':');

                if (key.equals("frequency") && frequency == null) {
                    frequency = number();
                } else if (key.equals("positions") && positions == null) {
                    positions = positions();
                } else {
                    throw new IllegalArgumentException(
                            "Campo desconocido o duplicado: " + key
                    );
                }
            } while (take(','));

            expect('}');

            if (frequency == null || positions == null
                    || frequency != positions.size()) {
                throw new IllegalArgumentException(
                        "Frecuencia o posiciones invalidas."
                );
            }

            return positions;
        }

        Map<String, Map<Integer, List<Integer>>> parse() {
            Map<String, Map<Integer, List<Integer>>> index =
                    new TreeMap<>();

            expect('{');

            if (!take('}')) {
                do {
                    String term = string();

                    if (!term.matches("[a-z]{3,}")
                            || index.containsKey(term)) {
                        throw new IllegalArgumentException(
                                "Termino invalido o duplicado: " + term
                        );
                    }

                    expect(':');
                    expect('{');

                    Map<Integer, List<Integer>> books = new TreeMap<>();

                    if (!take('}')) {
                        do {
                            String rawId = string();

                            if (!rawId.matches("0|[1-9][0-9]*")) {
                                throw new IllegalArgumentException(
                                        "ID invalido: " + rawId
                                );
                            }

                            int bookId = Integer.parseInt(rawId);
                            expect(':');

                            if (books.containsKey(bookId)) {
                                throw new IllegalArgumentException(
                                        "Libro duplicado: " + bookId
                                );
                            }

                            books.put(bookId, posting());
                        } while (take(','));

                        expect('}');
                    }

                    index.put(term, books);
                } while (take(','));

                expect('}');
            }

            whitespace();

            if (cursor != text.length()) {
                throw new IllegalArgumentException(
                        "Contenido adicional al final del JSON."
                );
            }

            return index;
        }
    }

    private void replaceFile(String content) throws IOException {
        Path target = outputPath.toAbsolutePath().normalize();
        Files.createDirectories(target.getParent());

        Path temporary = Files.createTempFile(
                target.getParent(), ".monolithic-", ".tmp"
        );

        try {
            Files.writeString(
                    temporary, content, StandardCharsets.UTF_8
            );

            try {
                Files.move(
                        temporary,
                        target,
                        StandardCopyOption.REPLACE_EXISTING,
                        StandardCopyOption.ATOMIC_MOVE
                );
            } catch (AtomicMoveNotSupportedException error) {
                Files.move(
                        temporary,
                        target,
                        StandardCopyOption.REPLACE_EXISTING
                );
            }
        } finally {
            Files.deleteIfExists(temporary);
        }
    }

    @Override
    public void saveIndexForBook(
            int bookId,
            Map<String, List<Integer>> positionDict
    ) throws Exception {
        if (bookId < 0) {
            throw new IllegalArgumentException("ID negativo.");
        }

        Map<String, Map<Integer, List<Integer>>> index =
                Files.exists(outputPath)
                        ? new Parser(Files.readString(
                                outputPath, StandardCharsets.UTF_8
                        )).parse()
                        : new TreeMap<>();

        // Retirar toda la version anterior del libro.
        for (Map<Integer, List<Integer>> books : index.values()) {
            books.remove(bookId);
        }

        index.entrySet().removeIf(entry -> entry.getValue().isEmpty());

        for (Map.Entry<String, List<Integer>> entry
                : positionDict.entrySet()) {
            if (!entry.getKey().matches("[a-z]{3,}")) {
                throw new IllegalArgumentException(
                        "Termino invalido: " + entry.getKey()
                );
            }

            int previous = -1;

            for (Integer position : entry.getValue()) {
                if (position == null || position <= previous) {
                    throw new IllegalArgumentException(
                            "Posiciones invalidas."
                    );
                }

                previous = position;
            }

            index.computeIfAbsent(
                    entry.getKey(), key -> new TreeMap<>()
            ).put(bookId, new ArrayList<>(entry.getValue()));
        }

        StringBuilder json = new StringBuilder("{\n");
        boolean firstTerm = true;

        for (Map.Entry<String, Map<Integer, List<Integer>>> term
                : index.entrySet()) {
            if (!firstTerm) {
                json.append(",\n");
            }

            firstTerm = false;
            json.append("  \"").append(term.getKey()).append("\": {");

            boolean firstBook = true;

            for (Map.Entry<Integer, List<Integer>> book
                    : term.getValue().entrySet()) {
                if (!firstBook) {
                    json.append(",");
                }

                firstBook = false;

                json.append("\n    \"").append(book.getKey())
                        .append("\": {\"frequency\": ")
                        .append(book.getValue().size())
                        .append(", \"positions\": ")
                        .append(book.getValue())
                        .append("}");
            }

            json.append("\n  }");
        }

        json.append("\n}\n");
        replaceFile(json.toString());
    }
}