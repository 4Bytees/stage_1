package indexer;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.*;

public class TsvIndexer extends BaseContainer {
    private final Path outputPath;

    public TsvIndexer() {
        this.outputPath = DATAMARTS_DIR.resolve("inverted_index_java.tsv");
    }

    @Override
    public void saveIndexForBook(int bookId, Map<String, List<Integer>> positionDict) throws Exception {
        Files.createDirectories(outputPath.getParent());

        try (BufferedWriter writer = Files.newBufferedWriter(
                outputPath, 
                StandardOpenOption.CREATE, 
                StandardOpenOption.APPEND)) {

            for (Map.Entry<String, List<Integer>> entry : positionDict.entrySet()) {
                String term = entry.getKey();
                List<Integer> positions = entry.getValue();
                writer.write(term + "\t" + bookId + "\t" + positions.size() + "\t" + positions.toString() + "\n");
            }
        }
    }
}