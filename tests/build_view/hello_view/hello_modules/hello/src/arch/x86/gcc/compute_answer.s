	.file	"compute_answer.c"
	.text
.globl _compute_answer
	.def	_compute_answer;	.scl	2;	.type	32;	.endef
_compute_answer:
	pushl	%ebp
	movl	%esp, %ebp
	movl	$42, %eax
	popl	%ebp
	ret
