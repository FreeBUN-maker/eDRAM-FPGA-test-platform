#ifndef SIM_TB_INCLUDE_LIBGEN_H
#define SIM_TB_INCLUDE_LIBGEN_H

#if defined(_WIN32)
static inline char *basename(char *path)
{
    char *base;

    if (path == 0 || path[0] == '\0') {
        return (char *)".";
    }

    base = path;
    for (char *cursor = path; *cursor != '\0'; ++cursor) {
        if (*cursor == '/' || *cursor == '\\') {
            base = cursor + 1;
        }
    }

    return (base[0] == '\0') ? (char *)"." : base;
}
#else
#include_next <libgen.h>
#endif

#endif
