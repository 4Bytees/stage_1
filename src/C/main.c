#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>

#ifdef _WIN32
#include <direct.h>
#define MKDIR(path) _mkdir(path)
#else
#include <sys/stat.h>
#define MKDIR(path) mkdir(path, 0755)
#endif

#define MAX_WORD_LEN 128
#define HASH_SIZE 4096

// Mismo conjunto de Stop Words utilizado en Python y Java
static const char *STOP_WORDS[] = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these", "they", "this", "to",
    NULL
};

int is_stop_word(const char *word) {
    for (int i = 0; STOP_WORDS[i] != NULL; i++) {
        if (strcmp(word, STOP_WORDS[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

typedef struct PositionNode {
    int pos;
    struct PositionNode *next;
} PositionNode;

typedef struct TermNode {
    char term[MAX_WORD_LEN];
    int count;
    PositionNode *positions_head;
    PositionNode *positions_tail;
    struct TermNode *next;
} TermNode;

TermNode *hash_table[HASH_SIZE];

unsigned int hash_func(const char *str) {
    unsigned int hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % HASH_SIZE;
}

void add_position(const char *term, int pos) {
    unsigned int idx = hash_func(term);
    TermNode *curr = hash_table[idx];
    while (curr != NULL) {
        if (strcmp(curr->term, term) == 0) {
            PositionNode *p = (PositionNode *)malloc(sizeof(PositionNode));
            p->pos = pos;
            p->next = NULL;
            curr->positions_tail->next = p;
            curr->positions_tail = p;
            curr->count++;
            return;
        }
        curr = curr->next;
    }

    TermNode *new_node = (TermNode *)malloc(sizeof(TermNode));
    strncpy(new_node->term, term, MAX_WORD_LEN - 1);
    new_node->term[MAX_WORD_LEN - 1] = '\0';
    new_node->count = 1;

    PositionNode *p = (PositionNode *)malloc(sizeof(PositionNode));
    p->pos = pos;
    p->next = NULL;
    new_node->positions_head = p;
    new_node->positions_tail = p;

    new_node->next = hash_table[idx];
    hash_table[idx] = new_node;
}

void clear_hash_table() {
    for (int i = 0; i < HASH_SIZE; i++) {
        TermNode *curr = hash_table[i];
        while (curr != NULL) {
            TermNode *temp_term = curr;
            PositionNode *p = curr->positions_head;
            while (p != NULL) {
                PositionNode *temp_p = p;
                p = p->next;
                free(temp_p);
            }
            curr = curr->next;
            free(temp_term);
        }
        hash_table[i] = NULL;
    }
}

void tokenize_file(const char *filepath) {
    FILE *f = fopen(filepath, "r");
    if (!f) return;

    char word[MAX_WORD_LEN];
    int word_len = 0;
    int pos = 0;
    int c;

    while ((c = fgetc(f)) != EOF) {
        if (isalpha(c)) {
            if (word_len < MAX_WORD_LEN - 1) {
                word[word_len++] = (char)tolower(c);
            }
        } else {
            if (word_len >= 3) {
                word[word_len] = '\0';
                if (!is_stop_word(word)) {
                    add_position(word, pos);
                }
            }
            if (word_len > 0) {
                pos++;
            }
            word_len = 0;
        }
    }

    if (word_len >= 3) {
        word[word_len] = '\0';
        if (!is_stop_word(word)) {
            add_position(word, pos);
        }
    }

    fclose(f);
}

void save_indices(int book_id) {
    MKDIR("datamarts");
    MKDIR("datamarts/inverted_index_folders_c");

    FILE *f_tsv = fopen("datamarts/inverted_index_c.tsv", "a");
    FILE *f_json = fopen("datamarts/inverted_index_c.json", "w");

    if (f_json) fprintf(f_json, "{\n");

    int first_term = 1;

    for (int i = 0; i < HASH_SIZE; i++) {
        TermNode *curr = hash_table[i];
        while (curr != NULL) {
            if (f_tsv) {
                fprintf(f_tsv, "%s\t%d\t%d\t[", curr->term, book_id, curr->count);
                PositionNode *p = curr->positions_head;
                while (p != NULL) {
                    fprintf(f_tsv, "%d%s", p->pos, p->next ? ", " : "");
                    p = p->next;
                }
                fprintf(f_tsv, "]\n");
            }

            char letter[2] = { (char)toupper(curr->term[0]), '\0' };
            char folder_path[256];
            snprintf(folder_path, sizeof(folder_path), "datamarts/inverted_index_folders_c/%s", letter);
            MKDIR(folder_path);

            char term_path[512];
            snprintf(term_path, sizeof(term_path), "%s/%s.txt", folder_path, curr->term);
            FILE *f_term = fopen(term_path, "a");
            if (f_term) {
                fprintf(f_term, "%d,%d,[", book_id, curr->count);
                PositionNode *p = curr->positions_head;
                while (p != NULL) {
                    fprintf(f_term, "%d%s", p->pos, p->next ? ", " : "");
                    p = p->next;
                }
                fprintf(f_term, "]\n");
                fclose(f_term);
            }

            if (f_json) {
                if (!first_term) fprintf(f_json, ",\n");
                fprintf(f_json, "  \"%s\": {\n    \"%d\": {\n      \"frequency\": %d,\n      \"positions\": [", 
                        curr->term, book_id, curr->count);
                PositionNode *p = curr->positions_head;
                while (p != NULL) {
                    fprintf(f_json, "%d%s", p->pos, p->next ? ", " : "");
                    p = p->next;
                }
                fprintf(f_json, "]\n    }\n  }");
                first_term = 0;
            }

            curr = curr->next;
        }
    }

    if (f_tsv) fclose(f_tsv);
    if (f_json) {
        fprintf(f_json, "\n}\n");
        fclose(f_json);
    }
}

int main() {
    printf("--- Starting C Inverted Indexing Process ---\n");

    int book_ids[] = {6, 7, 8, 9, 10};
    int num_books = 5;

    for (int i = 0; i < num_books; i++) {
        int book_id = book_ids[i];
        char filepath[256];
        snprintf(filepath, sizeof(filepath), "sample_data/%d_body.txt", book_id);

        clock_t start = clock();
        clear_hash_table();
        tokenize_file(filepath);
        save_indices(book_id);
        clock_t end = clock();

        double elapsed_ms = ((double)(end - start) / CLOCKS_PER_SEC) * 1000.0;
        printf("[C] Libro ID %d indexado en las 3 estructuras en %.2f ms.\n", book_id, elapsed_ms);
    }

    clear_hash_table();
    return 0;
}