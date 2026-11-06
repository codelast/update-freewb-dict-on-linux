/* fcitx_utils_read_uint32 的替代实现（小端 uint32）。
 * mb2txt.c 只外部依赖这一个符号，因此可以脱离 fcitx 库单独编译。 */
#include <stdio.h>
#include <stdint.h>

int fcitx_utils_read_uint32(FILE* fp, uint32_t* out)
{
    unsigned char b[4];
    if (fread(b, 1, 4, fp) != 4)
        return 0;
    *out = (uint32_t)b[0]
         | ((uint32_t)b[1] << 8)
         | ((uint32_t)b[2] << 16)
         | ((uint32_t)b[3] << 24);
    return 1;
}
