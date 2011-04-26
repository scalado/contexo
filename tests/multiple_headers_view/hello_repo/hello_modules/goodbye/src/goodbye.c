#include <stdio.h>
#include "header.h" 
#ifdef HELLO
#error wrong header included
#endif

int main(){
	printf("Contexo says Goodbye!\n");
}
