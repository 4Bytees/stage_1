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
#define HASH_SIZE 65536

static const char *STOP_WORDS[] = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for",
    "if", "in", "into", "is", "it", "no", "not", "of", "on", "or",
    "such", "that", "the", "their", "then", "there", "these", "they", "this", "to", "with", "from",
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "que", "de", "del", "en", "con", "por", "para", "su", "sus",
    NULL
};

int is_stop_word(const char *word) {
    for (int i = 0; STOP_WORDS[i] != NULL; i++) {
        if (strcmp(word, STOP_WORDS[i]) == 0) return 1;
    }
    return 0;
}

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

unsigned int hash_func(const char *str) {
    unsigned int hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % HASH_SIZE;
}

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

void tokenize_file(const char *filepath, int book_id) {
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
                    add_position_to_term(word, book_id, pos);
                }
            }
            if (word_len > 0) pos++;
            word_len = 0;
        }
    }

    if (word_len >= 3) {
        word[word_len] = '\0';
        if (!is_stop_word(word)) {
            add_position_to_term(word, book_id, pos);
        }
    }
    fclose(f);
}

void append_book_to_tsv_and_folders(int book_id) {
    MKDIR("datamarts");
    MKDIR("datamarts/inverted_index_folders_c");

    FILE *f_tsv = fopen("datamarts/inverted_index_c.tsv", "a");

    for (int i = 0; i < HASH_SIZE; i++) {
        TermNode *t = master_hash_table[i];
        while (t != NULL) {
            BookPosting *p = t->postings_head;
            while (p != NULL) {
                if (p->book_id == book_id) {
                    if (f_tsv) {
                        fprintf(f_tsv, "%s\t%d\t%d\t[", t->term, book_id, p->frequency);
                        PositionNode *pn = p->pos_head;
                        while (pn != NULL) {
                            fprintf(f_tsv, "%d%s", pn->pos, pn->next ? ", " : "");
                            pn = pn->next;
                        }
                        fprintf(f_tsv, "]\n");
                    }

                    char letter[2] = { (char)toupper(t->term[0]), '\0' };
                    char folder_path[256];
                    snprintf(folder_path, sizeof(folder_path), "datamarts/inverted_index_folders_c/%s", letter);
                    MKDIR(folder_path);

                    char term_path[512];
                    snprintf(term_path, sizeof(term_path), "%s/%s.txt", folder_path, t->term);
                    FILE *f_term = fopen(term_path, "a");
                    if (f_term) {
                        fprintf(f_term, "%d,%d,[", book_id, p->frequency);
                        PositionNode *pn = p->pos_head;
                        while (pn != NULL) {
                            fprintf(f_term, "%d%s", pn->pos, pn->next ? ", " : "");
                            pn = pn->next;
                        }
                        fprintf(f_term, "]\n");
                        fclose(f_term);
                    }
                    break;
                }
                p = p->next;
            }
            t = t->next;
        }
    }
    if (f_tsv) fclose(f_tsv);
}

void save_full_monolithic_json() {
    FILE *f_json = fopen("datamarts/inverted_index_c.json", "w");
    if (!f_json) return;

    fprintf(f_json, "{\n");
    int first_term = 1;

    for (int i = 0; i < HASH_SIZE; i++) {
        TermNode *t = master_hash_table[i];
        while (t != NULL) {
            if (!first_term) fprintf(f_json, ",\n");
            fprintf(f_json, "  \"%s\": {\n", t->term);

            BookPosting *p = t->postings_head;
            int first_book = 1;
            while (p != NULL) {
                if (!first_book) fprintf(f_json, ",\n");
                fprintf(f_json, "    \"%d\": {\n      \"frequency\": %d,\n      \"positions\": [", 
                        p->book_id, p->frequency);

                PositionNode *pn = p->pos_head;
                while (pn != NULL) {
                    fprintf(f_json, "%d%s", pn->pos, pn->next ? ", " : "");
                    pn = pn->next;
                }
                fprintf(f_json, "]\n    }");
                first_book = 0;
                p = p->next;
            }
            fprintf(f_json, "\n  }");
            first_term = 0;
            t = t->next;
        }
    }
    fprintf(f_json, "\n}\n");
    fclose(f_json);
}

#include <dirent.h>
#include <sys/stat.h>

void process_directory(const char *dir_path, int *total_processed) {
    DIR *dir = opendir(dir_path);
    if (!dir) return;
    
    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        
        char path[1024];
        snprintf(path, sizeof(path), "%s/%s", dir_path, ent->d_name);
        
        struct stat st;
        if (stat(path, &st) == 0) {
            if (S_ISDIR(st.st_mode)) {
                process_directory(path, total_processed);
            } else if (strstr(ent->d_name, "_body.txt")) {
                int book_id = 0;
                if (sscanf(ent->d_name, "%d_body.txt", &book_id) == 1) {
                    clock_t start = clock();
                    tokenize_file(path, book_id);
                    append_book_to_tsv_and_folders(book_id);
                    clock_t end = clock();
                    double elapsed_ms = ((double)(end - start) / CLOCKS_PER_SEC) * 1000.0;
                    printf("[C] Book ID %d indexed in %.2f ms.\n", book_id, elapsed_ms);
                    (*total_processed)++;
                }
            }
        }
    }
    closedir(dir);
}

int main(int argc, char *argv[]) {
    printf("--- Starting Dynamic C Inverted Indexing Process ---\n");
    const char *target_dir = (argc > 1) ? argv[1] : "../datalake"; 
    
    remove("datamarts/inverted_index_c.tsv");
    int total_processed = 0;
    process_directory(target_dir, &total_processed);
    
    save_full_monolithic_json();
    printf("[C] Completed. Total books indexed: %d. Index saved in datamarts/inverted_index_c.json\n", total_processed);
    return 0;
}