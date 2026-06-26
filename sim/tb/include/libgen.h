#ifndef SIM_TB_INCLUDE_LIBGEN_H
#define SIM_TB_INCLUDE_LIBGEN_H

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

#endif
