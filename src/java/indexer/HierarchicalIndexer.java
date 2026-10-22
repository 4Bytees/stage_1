package indexer;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.*;

public class HierarchicalIndexer extends BaseContainer {
    private final Path outputFolder;
    private static final Set<String> RESERVED_NAMES = Set.of(
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5",
        "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5",
        "LPT6", "LPT7", "LPT8", "LPT9"
    );

    public HierarchicalIndexer() {
        this.outputFolder = DATAMARTS_DIR.resolve("inverted_index_folders_java");
    }

    @Override
    public void saveIndexForBook(int bookId, Map<String, List<Integer>> positionDict) throws Exception {
        Files.createDirectories(outputFolder);

        for (Map.Entry<String, List<Integer>> entry : positionDict.entrySet()) {
            String word = entry.getKey();
            List<Integer> positions = entry.getValue();

            if (RESERVED_NAMES.contains(word.toUpperCase())) {
                continue;
            }

            char firstChar = Character.toUpperCase(word.charAt(0));
            if (!Character.isLetter(firstChar)) {
                continue;
            }

            Path letterDir = outputFolder.resolve(String.valueOf(firstChar));
            Files.createDirectories(letterDir);

            Path termFile = letterDir.resolve(word + ".txt");
            String line = bookId + "," + positions.size() + "," + positions.toString() + "\n";

            try (BufferedWriter writer = Files.newBufferedWriter(
                    termFile, 
                    StandardOpenOption.CREATE, 
                    StandardOpenOption.APPEND)) {
                writer.write(line);
            }
        }
    }
}