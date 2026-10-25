package indexer;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public abstract class BaseContainer {

    public static final Path BASE_DIR =
            Paths.get(".").toAbsolutePath().normalize();

    public static final Path DATAMARTS_DIR =
            BASE_DIR.resolve("datamarts");

    public static final Path DATALAKE_DIR =
            BASE_DIR.resolve("datalake");

    public static final Path SAMPLE_DATA_DIR =
            BASE_DIR.resolve("sample_data");

    protected static final Set<String> STOP_WORDS = Set.of(
            "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
            "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
            "such", "that", "the", "their", "then", "there", "these",
            "they", "this", "to"
    );


    private static final Pattern WORD_PATTERN = Pattern.compile(
            "\\b[a-z]{3,}\\b",
            Pattern.UNICODE_CHARACTER_CLASS
    );

    public Map<String, List<Integer>> tokenize(String text) {
        Map<String, List<Integer>> positionsByTerm = new TreeMap<>();

        Matcher matcher = WORD_PATTERN.matcher(
                text.toLowerCase(Locale.ROOT)
        );

        int position = 0;

        while (matcher.find()) {
            String term = matcher.group();

            if (!STOP_WORDS.contains(term)) {
                positionsByTerm
                        .computeIfAbsent(term, key -> new ArrayList<>())
                        .add(position);
            }

            position++;
        }

        return positionsByTerm;
    }

    public abstract void saveIndexForBook(
            int bookId,
            Map<String, List<Integer>> positionDict
    ) throws Exception;
}