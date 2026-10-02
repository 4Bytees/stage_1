package indexer;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public abstract class BaseContainer {
    public static final Path BASE_DIR = Paths.get(".").toAbsolutePath().normalize();
    public static final Path DATAMARTS_DIR = BASE_DIR.resolve("datamarts");
    public static final Path DATALAKE_DIR = BASE_DIR.resolve("datalake");
    public static final Path SAMPLE_DATA_DIR = BASE_DIR.resolve("sample_data");

    protected static final Set<String> STOP_WORDS = Set.of(
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
        "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
        "such", "that", "the", "their", "then", "there", "these", "they", "this", "to"
    );

    private static final Pattern WORD_PATTERN = Pattern.compile("\\b[a-z]{3,}\\b");

    public Map<String, List<Integer>> tokenize(String text) {
        Map<String, List<Integer>> positionDict = new HashMap<>();
        Matcher matcher = WORD_PATTERN.matcher(text.toLowerCase());
        int pos = 0;

        while (matcher.find()) {
            String word = matcher.group();
            if (!STOP_WORDS.contains(word)) {
                positionDict.computeIfAbsent(word, k -> new ArrayList<>()).add(pos);
            }
            pos++;
        }
        return positionDict;
    }

    public abstract void saveIndexForBook(int bookId, Map<String, List<Integer>> positionDict) throws Exception;
}