#include <stdio.h>
#include "private_hello.h"
#include "hello_dependency.h"

extern int compute_answer();

void hello(char* s) {
	// this is a comment
	int meaning_of_life = compute_answer();
	printf("Contexo says hello %s\nThe answer is %d\n", s, meaning_of_life);
}

