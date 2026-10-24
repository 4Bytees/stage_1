import indexer.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.Stream;

/**
 * Main entry point for the Java inverted-indexing engine.
 *
 * Usage (from the stage1/ project root after compiling):
 *   java -cp bin Main [data_directory]
 *
 * data_directory defaults to "sample_data" when omitted.
 * Pass "datalake" or a specific path to process the full corpus.
 */
public class Main {
    public static void main(String[] args) {
        System.out.println("--- Starting Dynamic Java Inverted Indexing Process ---");

        // Accept an optional path argument; default to sample_data for testing.
        Path targetDir = Paths.get(args.length > 0 ? args[0] : "sample_data");

        if (!Files.exists(targetDir)) {
            System.out.println("[JAVA ERROR] Directory not found: " + targetDir.toAbsolutePath());
            return;
        }

        MonolithicIndexer monolithic = new MonolithicIndexer();
        HierarchicalIndexer hierarchical = new HierarchicalIndexer();
        TsvIndexer tsvIndexer = new TsvIndexer();

        Pattern pattern = Pattern.compile("^(\\d+)_body\\.txt$");
        List<Path> files = new ArrayList<>();

        try (Stream<Path> stream = Files.walk(targetDir)) {
            stream.filter(Files::isRegularFile)
                  .filter(p -> p.getFileName().toString().endsWith("_body.txt"))
                  .forEach(files::add);
        } catch (Exception e) {
            System.err.println("[JAVA ERROR] Error walking directory " + targetDir + ": " + e.getMessage());
            return;
        }

        // Sort by book ID for deterministic ordering.
        files.sort(Comparator.comparingInt(p -> {
            Matcher m = pattern.matcher(p.getFileName().toString());
            return m.find() ? Integer.parseInt(m.group(1)) : 0;
        }));

        System.out.println("[JAVA] Total books detected for indexing: " + files.size());

        int successCount = 0;
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
                System.out.println("[JAVA] Book ID " + bookId + " indexed in " + duration + " ms.");
                successCount++;
            } catch (Exception e) {
                System.err.println("[JAVA ERROR] Failed to index book " + bookId + ": " + e.getMessage());
            }
        }

        System.out.println("[JAVA] Done. Successfully indexed " + successCount + "/" + files.size() + " books.");
    }
}