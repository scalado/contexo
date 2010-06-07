#include <stdint.h>
typedef int32_t v4si __attribute__((vector_size (16)));
v4si bar(v4si v1, v4si v2) {
	v4si vres = v1 * v2;
	return vres;
}
