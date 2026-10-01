import indexer.*;
import java.nio.file.*;
import java.util.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("--- Starting Java Inverted Indexing Process ---");

        Path sampleDir = Paths.get("sample_data");
        if (!Files.exists(sampleDir)) {
            System.out.println("[JAVA ERROR] Directorio sample_data no encontrado.");
            return;
        }

        MonolithicIndexer monolithic = new MonolithicIndexer();
        HierarchicalIndexer hierarchical = new HierarchicalIndexer();
        TsvIndexer tsvIndexer = new TsvIndexer();

        int[] bookIds = {6, 7, 8, 9, 10};

        for (int bookId : bookIds) {
            Path bodyFile = sampleDir.resolve(bookId + "_body.txt");
            if (!Files.exists(bodyFile)) {
                System.out.println("[JAVA] Libro " + bookId + "_body.txt no encontrado en sample_data.");
                continue;
            }

            try {
                long startTime = System.currentTimeMillis();
                String content = Files.readString(bodyFile);
                Map<String, List<Integer>> positionDict = monolithic.tokenize(content);

                monolithic.saveIndexForBook(bookId, positionDict);
                hierarchical.saveIndexForBook(bookId, positionDict);
                tsvIndexer.saveIndexForBook(bookId, positionDict);

                long duration = System.currentTimeMillis() - startTime;
                System.out.println("[JAVA] Libro ID " + bookId + " indexado en las 3 estructuras en " + duration + " ms.");
            } catch (Exception e) {
                System.err.println("[JAVA ERROR] Fallo al procesar libro " + bookId + ": " + e.getMessage());
            }
        }
    }
}