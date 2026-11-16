// Preserve the mathematical engine byte-for-byte. Darwin rejects Linux's
// one-GiB address/data limits. Cap live C++ allocations instead; the engine's
// power table and pair buffers all use std::vector. Normalize RSS units too.
#include <sys/resource.h>
#include <atomic>
#include <cstddef>
#include <cstdlib>
#include <new>

namespace {
std::atomic<std::size_t> four133_bytes{0};
std::atomic<std::size_t> four133_limit{1024ULL*1024*1024};
struct alignas(std::max_align_t) Header { std::size_t size; };
}

void* operator new(std::size_t size) {
    if (!size) size=1;
    const auto cap=four133_limit.load();
    if (size>cap) throw std::bad_alloc();
    const auto previous=four133_bytes.fetch_add(size);
    if (previous>cap-size) {
        four133_bytes.fetch_sub(size);
        throw std::bad_alloc();
    }
    auto* header=static_cast<Header*>(std::malloc(sizeof(Header)+size));
    if (!header) {
        four133_bytes.fetch_sub(size);
        throw std::bad_alloc();
    }
    header->size=size;
    return header+1;
}
void operator delete(void* pointer) noexcept {
    if (!pointer) return;
    auto* header=static_cast<Header*>(pointer)-1;
    four133_bytes.fetch_sub(header->size);
    std::free(header);
}
void* operator new[](std::size_t size) { return ::operator new(size); }
void operator delete[](void* pointer) noexcept { ::operator delete(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { ::operator delete(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { ::operator delete(pointer); }

static int four133_setrlimit(decltype(RLIMIT_AS) resource, const struct rlimit* limit) {
    if (resource != RLIMIT_AS) return setrlimit(resource,limit);
    if (limit->rlim_cur > 1024ULL*1024*1024 || limit->rlim_cur < four133_bytes.load()) return -1;
    four133_limit.store(limit->rlim_cur);
    return 0;
}

static int four133_getrusage(decltype(RUSAGE_SELF) who, struct rusage* usage) {
    const int status = getrusage(who, usage);
    if (!status) usage->ru_maxrss /= 1024;
    return status;
}

#define setrlimit four133_setrlimit
#define getrusage four133_getrusage
#ifdef FOUR133_MEMORY_SELFTEST
#define main four133_science_main
#endif
#include "../upstream/src/search.cpp"
#ifdef FOUR133_MEMORY_SELFTEST
#undef main
int main() {
    const auto baseline=four133_bytes.load();
    four133_limit.store(baseline+64);
    void* pointer=::operator new(32);
    if (four133_bytes.load()!=baseline+32) return 1;
    ::operator delete(pointer);
    if (four133_bytes.load()!=baseline) return 2;
    try {
        pointer=::operator new(128);
        ::operator delete(pointer);
        return 3;
    } catch (const std::bad_alloc&) { return four133_bytes.load()==baseline ? 0 : 4; }
}
#endif
