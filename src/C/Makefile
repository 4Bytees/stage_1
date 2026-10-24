CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -Wpedantic
CPPFLAGS =
LDFLAGS =
LDLIBS =

TARGET = ../../bin/indexer_c.exe
SRC = main.c

.PHONY: all clean rebuild

all: $(TARGET)

$(TARGET): $(SRC) Makefile
	mkdir -p "$(dir $(TARGET))"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SRC) $(LDFLAGS) $(LDLIBS) -o "$(TARGET)"

clean:
	rm -f "$(TARGET)"

rebuild:
	$(MAKE) clean
	$(MAKE) all