package indexer;

import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Stream;

public class HierarchicalIndexer extends BaseContainer {

    private final Path outputFolder;

    private static final Set<String> RESERVED_NAMES = Set.of(
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5",
            "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
            "LPT6", "LPT7", "LPT8", "LPT9"
    );

    public HierarchicalIndexer() {
        this(DATAMARTS_DIR.resolve("inverted_index_folders_java"));
    }

    public HierarchicalIndexer(Path outputFolder) {
        this.outputFolder = outputFolder;
    }

    public Path termPath(String term) {
        if (!term.matches("[a-z]{3,}")) {
            throw new IllegalArgumentException(
                    "Termino no valido: " + term
            );
        }

        String filename = RESERVED_NAMES.contains(
                term.toUpperCase(Locale.ROOT)
        )
                ? "__term_" + term + ".txt"
                : term + ".txt";

        return outputFolder
                .resolve(term.substring(0, 1).toUpperCase(Locale.ROOT))
                .resolve(filename);
    }

    private void replaceFile(Path target, String content) throws Exception {
        Files.createDirectories(target.getParent());

        Path temporary = Files.createTempFile(
                target.getParent(),
                ".posting-",
                ".tmp"
        );

        try {
            Files.writeString(
                    temporary,
                    content,
                    StandardCharsets.UTF_8
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
        Files.createDirectories(outputFolder);

        Map<Path, List<Integer>> newEntries = new HashMap<>();

        for (Map.Entry<String, List<Integer>> entry
                : positionDict.entrySet()) {
            newEntries.put(
                    termPath(entry.getKey()),
                    entry.getValue()
            );
        }

        Set<Path> paths = new TreeSet<>();

        try (Stream<Path> stream = Files.walk(outputFolder)) {
            stream.filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".txt"))
                    .forEach(paths::add);
        }

        paths.addAll(newEntries.keySet());

        for (Path path : paths) {
            List<String> remaining = new ArrayList<>();

            if (Files.exists(path)) {
                int lineNumber = 0;

                for (String line : Files.readAllLines(
                        path,
                        StandardCharsets.UTF_8
                )) {
                    lineNumber++;

                    if (line.isBlank()) {
                        continue;
                    }

                    String[] fields = line.split(",", 3);

                    if (fields.length != 3) {
                        throw new IllegalArgumentException(
                                "Invalid entry in " + path
                                        + ", line " + lineNumber
                        );
                    }

                    int existingBookId;

                    try {
                        existingBookId = Integer.parseInt(
                                fields[0].trim()
                        );
                    } catch (NumberFormatException error) {
                        throw new IllegalArgumentException(
                                "Invalid ID in " + path
                                        + ", line " + lineNumber,
                                error
                        );
                    }

                    if (existingBookId != bookId) {
                        remaining.add(line);
                    }
                }
            }

            if (newEntries.containsKey(path)) {
                List<Integer> positions = newEntries.get(path);

                remaining.add(
                        bookId + ","
                                + positions.size() + ","
                                + positions
                );
            }

            if (remaining.isEmpty()) {
                Files.deleteIfExists(path);
            } else {
                replaceFile(
                        path,
                        String.join("\n", remaining) + "\n"
                );
            }
        }
    }
}