
#ifdef __clang__
#warning "clang used"
#error "do not use clang"
#else
#warning "gcc used"
#endif

#include <stdlib.h>
#include <stdio.h>

int foo(int a, int b) {
return a+b;
}
