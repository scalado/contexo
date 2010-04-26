#include <stdio.h>
#include "private_hello.h"
#include "hello_dependency.h"

void hello(char* s) {
	// this is a comment
	printf("Contexo says hello %s\n", s);
}

