#include <stdint.h>
typedef v4si int32_t __attribute__((vector_size (16)));
v4si bar(v4si v1, v4si v2) {
	v4si vres = v1 * v2;
}
