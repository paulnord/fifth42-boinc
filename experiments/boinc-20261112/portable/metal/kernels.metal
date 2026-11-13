// 32-bit atomics suffice: host validation caps a packet at 50 million points.
// Coverage is accumulated from actual iterations, never assumed on the host.
kernel void enumerate_stream(device const Task* tasks [[buffer(0)]],
                             device const Chunk* chunks [[buffer(1)]],
                             device Candidate* hits [[buffer(2)]],
                             device atomic_uint* found [[buffer(3)]],
                             device atomic_uint* counts [[buffer(4)]],
                             constant uint& mode [[buffer(5)]],
                             constant ulong& cap [[buffer(6)]],
                             constant uint& capacity [[buffer(7)]],
                             uint3 group [[threadgroup_position_in_grid]],
                             uint lane [[thread_index_in_threadgroup]],
                             uint3 width [[threads_per_threadgroup]]) {
    const auto chunk=chunks[group.x];const auto task=tasks[chunk.task];uint visited=0;
    for(ulong j=lane;j<chunk.count;j+=width.x) {
        ++visited;Candidate hit{};
        if(evaluate(task,chunk.task,chunk.first+j,int(mode),cap,hit)) {
            const auto position=atomic_fetch_add_explicit(found,1u,memory_order_relaxed);
            if(position<capacity)hits[position]=hit;
        }
    }
    atomic_fetch_add_explicit(counts+chunk.task,visited,memory_order_relaxed);
}

kernel void arithmetic_cases(device const ArithmeticCase* cases [[buffer(0)]],
                             device ArithmeticResult* results [[buffer(1)]],
                             uint index [[thread_position_in_grid]]) {
    results[index]=arithmetic(cases[index]);
}
