CC = gcc
CFLAGS = -Wall -Wextra
LDFLAGS = -lwinmm

all: cat_platformer

cat_platformer: cat_platformer.c
	$(CC) $(CFLAGS) -o cat_platformer cat_platformer.c $(LDFLAGS)

clean:
	rm -f cat_platformer.exe 