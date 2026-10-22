CC = gcc
CFLAGS = -O3 -Wall
TARGET = ../../bin/indexer_c.exe
SRC = main.c

all: $(TARGET)

$(TARGET): $(SRC)
	mkdir -p ../../bin
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)