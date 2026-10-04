package indexer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

public class QueryBenchmark {
    public static List<Integer> queryHierarchical(Path basePath, String term) {
        term = term.toLowerCase();
        String initial = term.substring(0, 1).toUpperCase();
        Path target = basePath.resolve("inverted_index_folders_java").resolve(initial).resolve(term + ".txt");
        List<Integer> postings = new ArrayList<>();
        if (!Files.exists(target)) return postings;

        try {
            List<String> lines = Files.readAllLines(target);
            for (String l : lines) {
                if (!l.trim().isEmpty()) {
                    postings.add(Integer.parseInt(l.trim()));
                }
            }
        } catch (IOException | NumberFormatException ignored) {}
        return postings;
    }
}