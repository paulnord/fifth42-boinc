// Preserve the mathematical engine byte-for-byte. Darwin reserves a large
// virtual address range and rejects Linux's one-GiB RLIMIT_AS. Bound the data
// segment (heap) instead, and normalize Darwin's byte-valued maximum RSS.
#include <sys/resource.h>

static int four133_setrlimit(int resource, const struct rlimit* limit) {
    return setrlimit(resource == RLIMIT_AS ? RLIMIT_DATA : resource, limit);
}

static int four133_getrusage(int who, struct rusage* usage) {
    const int status = getrusage(who, usage);
    if (!status) usage->ru_maxrss /= 1024;
    return status;
}

#define setrlimit four133_setrlimit
#define getrusage four133_getrusage
#include "../upstream/src/search.cpp"
