CC = gcc
CFLAGS = -O3 -Wall
TARGET = ../../bin/indexer_c.exe
SRC = main.c

all: $(TARGET)

$(TARGET): $(SRC)
	@if not exist "..\..\bin" mkdir "..\..\bin"
	$(CC) $(CFLAGS) -o $(TARGET) $(SRC)

clean:
	@if exist $(TARGET) del $(TARGET)