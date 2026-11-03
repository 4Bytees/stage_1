/*
 * main.c  –  Stage-1 C Inverted Indexing Engine
 *
 * Tokenises every *_body.txt file found recursively under a target directory,
 * builds an in-memory inverted index using a hash table, then exports:
 *   - datamarts/inverted_index_c.json          (monolithic JSON)
 *   - datamarts/inverted_index_c.tsv           (tabular TSV)
 *   - datamarts/inverted_index_folders_c/X/    (hierarchical folders)
 *
 * Build (from stage1/ root):
 *   gcc -O2 -o bin/indexer_c src/C/main.c
 *
 * Usage:
 *   bin/indexer_c [data_directory]
 *   Defaults to "sample_data" when no argument is provided.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <dirent.h>
#include <sys/stat.h>
#include <errno.h>

#ifdef _WIN32
#include <direct.h>
#define MKDIR(path) _mkdir(path)
#else
#define MKDIR(path) mkdir(path, 0755)
#endif

/* -------------------------------------------------------------------------
 * Constants
 * --------------------------------------------------------------------- */
#define MAX_WORD_LEN 128
#define HASH_SIZE    65536

/* -------------------------------------------------------------------------
 * Stop-word table (identical to Python and Java implementations)
 * --------------------------------------------------------------------- */
static const char *STOP_WORDS[] = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these",
    "they", "this", "to",
    NULL
};

int is_stop_word(const char *word) {
    for (int i = 0; STOP_WORDS[i] != NULL; i++) {
        if (strcmp(word, STOP_WORDS[i]) == 0) return 1;
    }
    return 0;
}

/* -------------------------------------------------------------------------
 * Data structures
 * --------------------------------------------------------------------- */
typedef struct PositionNode {
    int pos;
    struct PositionNode *next;
} PositionNode;

typedef struct BookPosting {
    int book_id;
    int frequency;
    PositionNode *pos_head;
    PositionNode *pos_tail;
    struct BookPosting *next;
} BookPosting;

typedef struct TermNode {
    char term[MAX_WORD_LEN];
    BookPosting *postings_head;
    struct TermNode *next;
} TermNode;

TermNode *master_hash_table[HASH_SIZE];

/* -------------------------------------------------------------------------
 * Hash function (DJB2)
 * --------------------------------------------------------------------- */
unsigned int hash_func(const char *str) {
    unsigned int hash = 5381;
    int c;
    while ((c = (unsigned char)*str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % HASH_SIZE;
}

/* -------------------------------------------------------------------------
 * Index construction helpers
 * --------------------------------------------------------------------- */
TermNode *get_or_create_term(const char *term) {
    unsigned int idx = hash_func(term);
    TermNode *curr = master_hash_table[idx];
    while (curr != NULL) {
        if (strcmp(curr->term, term) == 0) return curr;
        curr = curr->next;
    }
    TermNode *new_term = (TermNode *)malloc(sizeof(TermNode));
    strncpy(new_term->term, term, MAX_WORD_LEN - 1);
    new_term->term[MAX_WORD_LEN - 1] = '\0';
    new_term->postings_head = NULL;
    new_term->next = master_hash_table[idx];
    master_hash_table[idx] = new_term;
    return new_term;
}

void add_position_to_term(const char *term, int book_id, int pos) {
    TermNode *t = get_or_create_term(term);
    BookPosting *p = t->postings_head;
    while (p != NULL) {
        if (p->book_id == book_id) break;
        p = p->next;
    }
    if (p == NULL) {
        p = (BookPosting *)malloc(sizeof(BookPosting));
        p->book_id = book_id;
        p->frequency = 0;
        p->pos_head = NULL;
        p->pos_tail = NULL;
        p->next = t->postings_head;
        t->postings_head = p;
    }
    PositionNode *pos_node = (PositionNode *)malloc(sizeof(PositionNode));
    pos_node->pos = pos;
    pos_node->next = NULL;
    if (p->pos_tail == NULL) {
        p->pos_head = pos_node;
        p->pos_tail = pos_node;
    } else {
        p->pos_tail->next = pos_node;
        p->pos_tail = pos_node;
    }
    p->frequency++;
}

/* -------------------------------------------------------------------------
 * Tokeniser (matches Python/Java: lowercase alpha tokens of length >= 3)
 * --------------------------------------------------------------------- */
static int is_ascii_letter(int c) {
    return (c >= 'a' && c <= 'z') ||
           (c >= 'A' && c <= 'Z');
}

static int ascii_lower(int c) {
    if (c >= 'A' && c <= 'Z') {
        return c + ('a' - 'A');
    }

    return c;
}

static void consume_token(
    const char *word,
    size_t length,
    int invalid,
    int book_id,
    int *position
) {
    if (invalid || length < 3) {
        return;
    }

    /*
     * No truncar silenciosamente palabras que no caben en TermNode.
     * Hasta cambiar esa estructura, fallar de forma explicita.
     */
    if (length >= MAX_WORD_LEN) {
        fprintf(
            stderr,
            "[C ERROR] Token demasiado largo en el libro %d.\n",
            book_id
        );
        exit(EXIT_FAILURE);
    }

    if (!is_stop_word(word)) {
        add_position_to_term(word, book_id, *position);
    }

    (*position)++;
}

void tokenize_file(const char *filepath, int book_id) {
    FILE *file = fopen(filepath, "rb");

    if (file == NULL) {
        fprintf(
            stderr,
            "[C ERROR] No se puede abrir: %s\n",
            filepath
        );
        exit(EXIT_FAILURE);
    }

    char word[MAX_WORD_LEN];
    size_t length = 0;
    int invalid = 0;
    int position = 0;
    int c;

    while ((c = fgetc(file)) != EOF) {
        int belongs_to_group =
                is_ascii_letter(c) ||
                (c >= '0' && c <= '9') ||
                c == '_';

        if (belongs_to_group) {
            if (
                (c >= '0' && c <= '9') ||
                c == '_'
            ) {
                invalid = 1;
            }

            if (length < MAX_WORD_LEN - 1) {
                word[length] = (char)ascii_lower(c);
            }

            length++;
        } else {
            size_t end = (
                length < MAX_WORD_LEN
                ? length
                : MAX_WORD_LEN - 1
            );

            word[end] = '\0';

            consume_token(
                word,
                length,
                invalid,
                book_id,
                &position
            );

            length = 0;
            invalid = 0;
        }
}

    if (ferror(file)) {
        fprintf(
                stderr,
                "[C ERROR] Error leyendo: %s\n",
                filepath
        );
        fclose(file);
        exit(EXIT_FAILURE);
    }

    size_t end = (
            length < MAX_WORD_LEN
            ? length
            : MAX_WORD_LEN - 1
    );

    word[end] = '\0';

    consume_token(
            word,
            length,
            invalid,
            book_id,
            &position
    );

    if (fclose(file) != 0) {
        fprintf(
                stderr,
                "[C ERROR] Error cerrando: %s\n",
                filepath
        );
        exit(EXIT_FAILURE);
    }
}

/* -------------------------------------------------------------------------
 * Output: TSV + hierarchical folders (appended per book)
 *
 * Posting line format (mirrors Python and Java):
 *   <book_id>,<frequency>,[<p1>, <p2>, ...]
 * --------------------------------------------------------------------- */
/* Exporta el indice completo construido en memoria.
 * Cada archivo de termino se escribe una sola vez.
 * Devuelve 0 si todo va bien y -1 si falla alguna escritura.
 */

 static int is_windows_reserved_name(const char *term) {
    static const char *reserved[] = {
        "con", "prn", "aux", "nul",
        "com1", "com2", "com3", "com4", "com5",
        "com6", "com7", "com8", "com9",
        "lpt1", "lpt2", "lpt3", "lpt4", "lpt5",
        "lpt6", "lpt7", "lpt8", "lpt9",
        NULL
    };

    for (size_t i = 0; reserved[i] != NULL; i++) {
        if (strcmp(term, reserved[i]) == 0) {
            return 1;
        }
    }

    return 0;
}

static int replace_file(const char *temporary_path, const char *target_path) {
    /*
     * En Windows, rename() normalmente no sustituye un archivo existente.
     * Se elimina primero el destino.
     *
     * Esto no ofrece atomicidad completa en Windows, pero evita dejar
     * un archivo parcialmente escrito si falla la generación temporal.
     */
    if (remove(target_path) != 0 && errno != ENOENT) {
        perror(target_path);
        remove(temporary_path);
        return -1;
    }

    if (rename(temporary_path, target_path) != 0) {
        perror(target_path);
        remove(temporary_path);
        return -1;
    }

    return 0;
}

int save_tsv_and_folders(void) {
    const char *root = "datamarts/inverted_index_folders_c";
    const char *tsv_path = "datamarts/inverted_index_c.tsv";
    const char *tsv_temporary =
            "datamarts/.inverted_index_c.tsv.tmp";

    if (MKDIR("datamarts") != 0 && errno != EEXIST) {
        perror("datamarts");
        return -1;
    }

    if (MKDIR(root) != 0 && errno != EEXIST) {
        perror(root);
        return -1;
    }

    FILE *tsv = fopen(tsv_temporary, "w");

    if (tsv == NULL) {
        perror(tsv_temporary);
        return -1;
    }

    int failed = 0;

    for (int i = 0; i < HASH_SIZE; i++) {
        for (
            TermNode *term_node = master_hash_table[i];
            term_node != NULL;
            term_node = term_node->next
        ) {
            const char *term = term_node->term;

            if (term == NULL || term[0] == '\0') {
                fprintf(stderr, "[C ERROR] Termino vacio.\n");
                failed = 1;
                continue;
            }

            char folder[512];
            char filename[512];
            char target_path[1024];
            char temporary_path[1100];

            int written = snprintf(
                folder,
                sizeof(folder),
                "%s/%c",
                root,
                toupper((unsigned char)term[0])
            );

            if (
                written < 0 ||
                (size_t)written >= sizeof(folder)
            ) {
                fprintf(
                    stderr,
                    "[C ERROR] Ruta de carpeta demasiado larga: %s\n",
                    term
                );
                failed = 1;
                continue;
            }

            if (MKDIR(folder) != 0 && errno != EEXIST) {
                perror(folder);
                failed = 1;
                continue;
            }

            /*
             * Mismo convenio que Python y Java:
             *
             * normal    -> apple.txt
             * reservado -> __term_con.txt
             */
            written = snprintf(
                filename,
                sizeof(filename),
                is_windows_reserved_name(term)
                    ? "__term_%s.txt"
                    : "%s.txt",
                term
            );

            if (
                written < 0 ||
                (size_t)written >= sizeof(filename)
            ) {
                fprintf(
                    stderr,
                    "[C ERROR] Nombre de archivo demasiado largo: %s\n",
                    term
                );
                failed = 1;
                continue;
            }

            written = snprintf(
                target_path,
                sizeof(target_path),
                "%s/%s",
                folder,
                filename
            );

            if (
                written < 0 ||
                (size_t)written >= sizeof(target_path)
            ) {
                fprintf(
                    stderr,
                    "[C ERROR] Ruta demasiado larga: %s\n",
                    term
                );
                failed = 1;
                continue;
            }

            written = snprintf(
                temporary_path,
                sizeof(temporary_path),
                "%s.tmp",
                target_path
            );

            if (
                written < 0 ||
                (size_t)written >= sizeof(temporary_path)
            ) {
                fprintf(
                    stderr,
                    "[C ERROR] Ruta temporal demasiado larga: %s\n",
                    term
                );
                failed = 1;
                continue;
            }

            FILE *term_file = fopen(temporary_path, "w");

            if (term_file == NULL) {
                perror(temporary_path);
                failed = 1;
                continue;
            }

            for (
                BookPosting *posting = term_node->postings_head;
                posting != NULL;
                posting = posting->next
            ) {
                if (
                    fprintf(
                        tsv,
                        "%s\t%d\t%d\t[",
                        term,
                        posting->book_id,
                        posting->frequency
                    ) < 0
                ) {
                    failed = 1;
                }

                if (
                    fprintf(
                        term_file,
                        "%d,%d,[",
                        posting->book_id,
                        posting->frequency
                    ) < 0
                ) {
                    failed = 1;
                }

                for (
                    PositionNode *position = posting->pos_head;
                    position != NULL;
                    position = position->next
                ) {
                    const char *separator =
                            position->next != NULL ? ", " : "";

                    if (
                        fprintf(
                            tsv,
                            "%d%s",
                            position->pos,
                            separator
                        ) < 0
                    ) {
                        failed = 1;
                    }

                    if (
                        fprintf(
                            term_file,
                            "%d%s",
                            position->pos,
                            separator
                        ) < 0
                    ) {
                        failed = 1;
                    }
                }

                if (fprintf(tsv, "]\n") < 0) {
                    failed = 1;
                }

                if (fprintf(term_file, "]\n") < 0) {
                    failed = 1;
                }
            }

            if (fflush(term_file) != 0) {
                perror(temporary_path);
                failed = 1;
            }

            if (ferror(term_file)) {
                fprintf(
                    stderr,
                    "[C ERROR] Error escribiendo %s\n",
                    temporary_path
                );
                failed = 1;
            }

            if (fclose(term_file) != 0) {
                perror(temporary_path);
                failed = 1;
            }

            if (failed) {
                remove(temporary_path);
                continue;
            }

            if (
                replace_file(
                    temporary_path,
                    target_path
                ) != 0
            ) {
                failed = 1;
            }
        }
    }

    if (fflush(tsv) != 0) {
        perror(tsv_temporary);
        failed = 1;
    }

    if (ferror(tsv)) {
        fprintf(
            stderr,
            "[C ERROR] Error escribiendo %s\n",
            tsv_temporary
        );
        failed = 1;
    }

    if (fclose(tsv) != 0) {
        perror(tsv_temporary);
        failed = 1;
    }

    if (failed) {
        remove(tsv_temporary);
        return -1;
    }

    if (replace_file(tsv_temporary, tsv_path) != 0) {
        return -1;
    }

    return 0;
}
/* -------------------------------------------------------------------------
 * Output: monolithic JSON
 * --------------------------------------------------------------------- */
int save_full_monolithic_json(void) {
    const char *target_path =
            "datamarts/inverted_index_c.json";

    const char *temporary_path =
            "datamarts/.inverted_index_c.json.tmp";

    FILE *json = fopen(temporary_path, "w");

    if (json == NULL) {
        perror(temporary_path);
        return -1;
    }

    int failed = 0;

    if (fprintf(json, "{\n") < 0) {
        failed = 1;
    }

    int first_term = 1;

    for (int i = 0; i < HASH_SIZE; i++) {
        for (
            TermNode *term = master_hash_table[i];
            term != NULL;
            term = term->next
        ) {
            if (!first_term && fprintf(json, ",\n") < 0) {
                failed = 1;
            }

            if (
                fprintf(
                    json,
                    "  \"%s\": {",
                    term->term
                ) < 0
            ) {
                failed = 1;
            }

            int first_book = 1;

            for (
                BookPosting *posting = term->postings_head;
                posting != NULL;
                posting = posting->next
            ) {
                if (!first_book && fprintf(json, ",") < 0) {
                    failed = 1;
                }

                if (
                    fprintf(
                        json,
                        "\n    \"%d\": {"
                        "\"frequency\": %d, "
                        "\"positions\": [",
                        posting->book_id,
                        posting->frequency
                    ) < 0
                ) {
                    failed = 1;
                }

                for (
                    PositionNode *position = posting->pos_head;
                    position != NULL;
                    position = position->next
                ) {
                    if (
                        fprintf(
                            json,
                            "%d%s",
                            position->pos,
                            position->next != NULL ? ", " : ""
                        ) < 0
                    ) {
                        failed = 1;
                    }
                }

                if (fprintf(json, "]}") < 0) {
                    failed = 1;
                }

                first_book = 0;
            }

            if (fprintf(json, "\n  }") < 0) {
                failed = 1;
            }

            first_term = 0;
        }
    }

    if (fprintf(json, "\n}\n") < 0) {
        failed = 1;
    }

    if (fflush(json) != 0) {
        perror(temporary_path);
        failed = 1;
    }

    if (ferror(json)) {
        fprintf(
            stderr,
            "[C ERROR] Error escribiendo %s\n",
            temporary_path
        );
        failed = 1;
    }

    if (fclose(json) != 0) {
        perror(temporary_path);
        failed = 1;
    }

    if (failed) {
        remove(temporary_path);
        return -1;
    }

    if (replace_file(temporary_path, target_path) != 0) {
        return -1;
    }

    return 0;
}
/* -------------------------------------------------------------------------
 * Recursive directory traversal (POSIX opendir / readdir)
 * Compatible with MinGW on Windows and GCC on Linux/macOS.
 * --------------------------------------------------------------------- */
void process_directory(const char *dir_path, int *total_processed) {
    DIR *dir = opendir(dir_path);
    if (!dir) {
        fprintf(stderr, "[C WARNING] Cannot open directory: %s\n", dir_path);
        return;
    }
    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0)
            continue;

        char path[1024];
        snprintf(path, sizeof(path), "%s/%s", dir_path, ent->d_name);

        struct stat st;
        if (stat(path, &st) != 0) continue;

        if (S_ISDIR(st.st_mode)) {
            process_directory(path, total_processed);
        } else if (strstr(ent->d_name, "_body.txt")) {
            int book_id = 0;
            if (sscanf(ent->d_name, "%d_body.txt", &book_id) == 1) {
                clock_t start = clock();
                tokenize_file(path, book_id);
                clock_t end = clock();
                double elapsed_ms = ((double)(end - start) / CLOCKS_PER_SEC) * 1000.0;
                printf("[C] Book ID %d indexed in %.2f ms.\n", book_id, elapsed_ms);
                (*total_processed)++;
            }
        }
    }
    closedir(dir);
}

/* -------------------------------------------------------------------------
 * Entry point
 * --------------------------------------------------------------------- */
int main(int argc, char *argv[]) {
    printf("--- Starting Dynamic C Inverted Indexing Process ---\n");

    const char *target_dir = (argc > 1)
            ? argv[1]
            : "sample_data";

    printf("[C] Processing directory: %s\n", target_dir);
    fflush(stdout);

    memset(master_hash_table, 0, sizeof(master_hash_table));

    int total_processed = 0;

    /* Recorrer el corpus UNA sola vez. */
    process_directory(target_dir, &total_processed);

    if (total_processed == 0) {
        fprintf(stderr, "[C ERROR] No se han procesado libros.\n");
        return EXIT_FAILURE;
    }

    printf(
        "[C] Recorrido terminado. Libros procesados: %d.\n",
        total_processed
    );

    printf("[C] Exportando TSV y archivos jerarquicos...\n");
    fflush(stdout);

    if (save_tsv_and_folders() != 0) {
        fprintf(
            stderr,
            "[C ERROR] Fallo al exportar TSV o jerarquico.\n"
        );
        return EXIT_FAILURE;
    }

    printf("[C] Exportacion TSV y jerarquica terminada.\n");
    printf("[C] Exportando JSON...\n");
    fflush(stdout);

    if (save_full_monolithic_json() != 0) {
        fprintf(
            stderr,
            "[C ERROR] Fallo al exportar el JSON monolitico.\n"
        );
        return EXIT_FAILURE;
    }

    printf("[C] Exportacion JSON terminada correctamente.\n");
    printf(
        "[C] Finalizado. Total de libros procesados: %d.\n",
        total_processed
    );
    fflush(stdout);

    return EXIT_SUCCESS;
}