package indexer;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class MonolithicIndexer extends BaseContainer {
    private final Path outputPath;
    private final Map<String, Map<Integer, List<Integer>>> masterIndex;

    public MonolithicIndexer() {
        this.outputPath = DATAMARTS_DIR.resolve("inverted_index_java.json");
        this.masterIndex = new TreeMap<>();
    }

    @Override
    public void saveIndexForBook(int bookId, Map<String, List<Integer>> positionDict) throws Exception {
        Files.createDirectories(outputPath.getParent());

        for (Map.Entry<String, List<Integer>> entry : positionDict.entrySet()) {
            masterIndex.computeIfAbsent(entry.getKey(), k -> new TreeMap<>())
                       .put(bookId, new ArrayList<>(entry.getValue()));
        }

        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        int termCount = 0;
        int totalTerms = masterIndex.size();

        for (Map.Entry<String, Map<Integer, List<Integer>>> termEntry : masterIndex.entrySet()) {
            String word = termEntry.getKey();
            Map<Integer, List<Integer>> books = termEntry.getValue();

            sb.append("  \"").append(word).append("\": {\n");
            int bookCount = 0;
            int totalBooks = books.size();

            for (Map.Entry<Integer, List<Integer>> bookEntry : books.entrySet()) {
                int bId = bookEntry.getKey();
                List<Integer> positions = bookEntry.getValue();

                sb.append("    \"").append(bId).append("\": {\n");
                sb.append("      \"frequency\": ").append(positions.size()).append(",\n");
                sb.append("      \"positions\": ").append(positions.toString()).append("\n");
                sb.append("    }");

                bookCount++;
                if (bookCount < totalBooks) {
                    sb.append(",\n");
                } else {
                    sb.append("\n");
                }
            }

            sb.append("  }");
            termCount++;
            if (termCount < totalTerms) {
                sb.append(",\n");
            } else {
                sb.append("\n");
            }
        }
        sb.append("}\n");

        try (BufferedWriter writer = Files.newBufferedWriter(outputPath)) {
            writer.write(sb.toString());
        }
    }
}