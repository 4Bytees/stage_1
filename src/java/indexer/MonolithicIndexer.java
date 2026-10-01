package indexer;

import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class MonolithicIndexer extends BaseContainer {
    private final Path outputPath;

    public MonolithicIndexer() {
        this.outputPath = DATAMARTS_DIR.resolve("inverted_index_java.json");
    }

    @Override
    public void saveIndexForBook(int bookId, Map<String, List<Integer>> positionDict) throws Exception {
        Files.createDirectories(outputPath.getParent());
        
        // Serialización JSON nativa ligera y rápida sin librerías externas
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        int count = 0;
        int total = positionDict.size();

        for (Map.Entry<String, List<Integer>> entry : positionDict.entrySet()) {
            String word = entry.getKey();
            List<Integer> positions = entry.getValue();

            sb.append("  \"").append(word).append("\": {\n");
            sb.append("    \"").append(bookId).append("\": {\n");
            sb.append("      \"frequency\": ").append(positions.size()).append(",\n");
            sb.append("      \"positions\": ").append(positions.toString()).append("\n");
            sb.append("    }\n");
            sb.append("  }");

            count++;
            if (count < total) {
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