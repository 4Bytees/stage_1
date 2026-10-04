import indexer.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("--- Starting Dynamic Java Inverted Indexing Process ---");

        Path sampleDir = Paths.get("sample_data");
        if (!Files.exists(sampleDir)) {
            System.out.println("[JAVA ERROR] Directorio sample_data no encontrado.");
            return;
        }

        MonolithicIndexer monolithic = new MonolithicIndexer();
        HierarchicalIndexer hierarchical = new HierarchicalIndexer();
        TsvIndexer tsvIndexer = new TsvIndexer();

        Pattern pattern = Pattern.compile("^(\\d+)_body\\.txt$");
        List<Path> files = new ArrayList<>();

        try (DirectoryStream<Path> stream = Files.newDirectoryStream(sampleDir, "*_body.txt")) {
            for (Path entry : stream) {
                files.add(entry);
            }
        } catch (Exception e) {
            System.err.println("[JAVA ERROR] Error listando sample_data: " + e.getMessage());
            return;
        }

        files.sort(Comparator.comparingInt(p -> {
            Matcher m = pattern.matcher(p.getFileName().toString());
            return m.find() ? Integer.valueOf(m.group(1)) : 0;
        }));

        System.out.println("[JAVA] Total de libros detectados para indexar: " + files.size());

        for (Path bodyFile : files) {
            Matcher matcher = pattern.matcher(bodyFile.getFileName().toString());
            if (!matcher.find()) continue;
            int bookId = Integer.parseInt(matcher.group(1));

            try {
                long startTime = System.currentTimeMillis();
                String content = Files.readString(bodyFile);
                Map<String, List<Integer>> positionDict = monolithic.tokenize(content);

                monolithic.saveIndexForBook(bookId, positionDict);
                hierarchical.saveIndexForBook(bookId, positionDict);
                tsvIndexer.saveIndexForBook(bookId, positionDict);

                long duration = System.currentTimeMillis() - startTime;
                System.out.println("[JAVA] Libro ID " + bookId + " indexado en " + duration + " ms.");
            } catch (Exception e) {
                System.err.println("[JAVA ERROR] Fallo al procesar libro " + bookId + ": " + e.getMessage());
            }
        }
    }
}