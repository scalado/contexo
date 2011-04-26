#include <stdio.h>
#include "header.h" 
#ifdef GOODBYE
#error wrong header included
#endif

int main(){
	printf("Contexo says Hello!\n");
}
