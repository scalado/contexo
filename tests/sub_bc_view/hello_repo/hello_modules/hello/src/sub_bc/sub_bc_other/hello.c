
#ifdef __clang__
#warning "clang used"
#else
#warning "gcc used"
#error "do not use gcc"
#endif
#include <stdlib.h>
#include <stdio.h>

int main() {
	printf("it works!");
	exit(0);
}

