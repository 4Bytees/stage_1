import indexer.*;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.Stream;

public class Main {
    public static void main(String[] args) {
        System.out.println("--- Starting Dynamic Java Inverted Indexing Process ---");

        Path targetDir = Paths.get(args.length > 0 ? args[0] : "datalake");

        try {
            Files.deleteIfExists(Paths.get("datamarts/inverted_index_java.tsv"));
        } catch (IOException ignored) {}

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
            System.err.println("[JAVA ERROR] Error listing " + targetDir + ": " + e.getMessage());
            return;
        }

        files.sort(Comparator.comparingInt(p -> {
            Matcher m = pattern.matcher(p.getFileName().toString());
            return m.find() ? Integer.valueOf(m.group(1)) : 0;
        }));

        System.out.println("[JAVA] Total number of books detected for indexing: " + files.size());

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
            } catch (Exception e) {
                System.err.println("[JAVA ERROR] Error processing book " + bookId + ": " + e.getMessage());
            }
        }
    }
}