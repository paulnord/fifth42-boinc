#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "stream_io.hpp"
#include "metal_shader.hpp"
#include <cstring>
#include <cstdlib>

static_assert(sizeof(Task)==120 && sizeof(Chunk)==24 && sizeof(Candidate)==40,"Metal ABI");
inline std::string error_text(NSError* error) {
    return error?std::string([[error localizedDescription] UTF8String]):"unknown Metal error";
}
struct Buffer {
    id<MTLBuffer> value=nil;std::size_t bytes=0;
    void reserve(id<MTLDevice> device,std::size_t wanted) {
        wanted=std::max<std::size_t>(wanted,8);if(wanted<=bytes)return;
        auto replacement=[device newBufferWithLength:wanted options:MTLResourceStorageModeShared];
        if(!replacement)throw std::runtime_error("Metal allocation failed");
        value=replacement;bytes=wanted;
    }
};
id<MTLComputePipelineState> pipeline(id<MTLDevice> device,id<MTLLibrary> library,NSString* name) {
    auto function=[library newFunctionWithName:name];
    if(!function)throw std::runtime_error("missing Metal entry point");
    NSError* error=nil;auto result=[device newComputePipelineStateWithFunction:function error:&error];
    if(!result)throw std::runtime_error("Metal pipeline: "+error_text(error));
    return result;
}
void finish(id<MTLCommandBuffer> command) {
    [command commit];[command waitUntilCompleted];
    if(command.status!=MTLCommandBufferStatusCompleted)
        throw std::runtime_error("Metal command failed: "+error_text(command.error));
}
int main(int argc,char** argv) {
    @autoreleasepool {
      try {
        protect_parent();
        auto devices=MTLCopyAllDevices();
        if(argc==2 && std::string(argv[1])=="--list-devices") {
            std::cout<<"{\"devices\":[";bool first=true;
            for(id<MTLDevice> device in devices) {
                if(!first)std::cout<<',';first=false;
                std::cout<<"{\"name\":"<<quote([device.name UTF8String])
                    <<",\"registry_id\":"<<quote(std::to_string(device.registryID))
                    <<",\"unified_memory\":"<<(device.hasUnifiedMemory?"true":"false")<<'}';
            }
            std::cout<<"]}\n";return 0;
        }
        const char* allocated=std::getenv("FIFTH42_METAL_REGISTRY_ID");
        if(!allocated || !*allocated)throw std::runtime_error("explicit FIFTH42_METAL_REGISTRY_ID required");
        std::string allocation(allocated);
        if(allocation.find_first_not_of("0123456789")!=std::string::npos)throw std::runtime_error("invalid Metal registry ID");
        std::size_t used=0;auto registry=std::stoull(allocation,&used);
        if(used!=allocation.size())throw std::runtime_error("invalid Metal registry ID");
        id<MTLDevice> device=nil;
        for(id<MTLDevice> candidate in devices)if(candidate.registryID==registry){device=candidate;break;}
        if(!device)throw std::runtime_error("allocated Metal device unavailable; no CPU fallback");
        const bool arithmetic_mode=argc==2 && std::string(argv[1])=="--arithmetic";
        const auto hit_capacity=arithmetic_mode ? 65536u : ::capacity(argc,argv);
        NSError* error=nil;auto options=[MTLCompileOptions new];options.languageVersion=MTLLanguageVersion2_4;
        auto library=[device newLibraryWithSource:[NSString stringWithUTF8String:fifth42_shader] options:options error:&error];
        if(!library)throw std::runtime_error("Metal shader compile: "+error_text(error));
        auto compute=pipeline(device,library,arithmetic_mode?@"arithmetic_cases":@"enumerate_stream");
        auto queue=[device newCommandQueue];if(!queue)throw std::runtime_error("Metal queue allocation failed");
        Buffer tasks,chunks,hits,found,counts;
        if(arithmetic_mode) {
            const auto cases=read_arithmetic();Buffer input,output;
            input.reserve(device,cases.size()*sizeof(ArithmeticCase));output.reserve(device,cases.size()*sizeof(ArithmeticResult));
            if(!cases.empty()) {
                std::memcpy(input.value.contents,cases.data(),cases.size()*sizeof(ArithmeticCase));
                auto command=[queue commandBuffer];auto encoder=[command computeCommandEncoder];
                if(!command||!encoder)throw std::runtime_error("Metal arithmetic encoder failed");
                [encoder setComputePipelineState:compute];[encoder setBuffer:input.value offset:0 atIndex:0];
                [encoder setBuffer:output.value offset:0 atIndex:1];
                const auto width=std::min<NSUInteger>(256,compute.maxTotalThreadsPerThreadgroup);
                [encoder dispatchThreads:MTLSizeMake(cases.size(),1,1) threadsPerThreadgroup:MTLSizeMake(width,1,1)];
                [encoder endEncoding];finish(command);
            }
            std::vector<ArithmeticResult> result(cases.size());
            if(!result.empty())std::memcpy(result.data(),output.value.contents,result.size()*sizeof(ArithmeticResult));
            print_arithmetic("gpu",result);return 0;
        }
        hits.reserve(device,hit_capacity*sizeof(Candidate));found.reserve(device,sizeof(std::uint32_t));
        std::cout<<"{\"ready\":true,\"backend\":\"gpu\",\"gpu_api\":\"metal\",\"persistent\":true,\"device_registry_id\":"
            <<quote(allocation)<<",\"device_name\":"<<quote([device.name UTF8String])<<"}\n"<<std::flush;
        U64 previous=0,request=0;std::string payload;
        while(read_frame(request,payload,previous)) {
          @autoreleasepool {
            try {
                const auto began=Clock::now();const auto in=parse_frame(payload);
                tasks.reserve(device,in.tasks.size()*sizeof(Task));chunks.reserve(device,in.chunks.size()*sizeof(Chunk));
                counts.reserve(device,in.tasks.size()*sizeof(std::uint32_t));
                if(!in.tasks.empty())std::memcpy(tasks.value.contents,in.tasks.data(),in.tasks.size()*sizeof(Task));
                if(!in.chunks.empty())std::memcpy(chunks.value.contents,in.chunks.data(),in.chunks.size()*sizeof(Chunk));
                std::memset(found.value.contents,0,sizeof(std::uint32_t));
                std::memset(counts.value.contents,0,counts.bytes);
                double gpu_seconds=0;
                if(!in.chunks.empty()) {
                    auto command=[queue commandBuffer];auto encoder=[command computeCommandEncoder];
                    if(!command||!encoder)throw std::runtime_error("Metal encoder failed");
                    [encoder setComputePipelineState:compute];
                    [encoder setBuffer:tasks.value offset:0 atIndex:0];[encoder setBuffer:chunks.value offset:0 atIndex:1];
                    [encoder setBuffer:hits.value offset:0 atIndex:2];[encoder setBuffer:found.value offset:0 atIndex:3];
                    [encoder setBuffer:counts.value offset:0 atIndex:4];
                    const std::uint32_t mode=in.mode;
                    [encoder setBytes:&mode length:sizeof(mode) atIndex:5];[encoder setBytes:&in.cap length:sizeof(in.cap) atIndex:6];
                    [encoder setBytes:&hit_capacity length:sizeof(hit_capacity) atIndex:7];
                    const auto width=std::min<NSUInteger>(256,compute.maxTotalThreadsPerThreadgroup);
                    [encoder dispatchThreadgroups:MTLSizeMake(in.chunks.size(),1,1) threadsPerThreadgroup:MTLSizeMake(width,1,1)];
                    [encoder endEncoding];finish(command);
                    gpu_seconds=std::max(0.0,command.GPUEndTime-command.GPUStartTime);
                }
                const auto size=*static_cast<const std::uint32_t*>(found.value.contents);
                if(size>hit_capacity)throw std::runtime_error("candidate capacity exceeded; no coverage");
                std::vector<Candidate> output(size);if(size)std::memcpy(output.data(),hits.value.contents,size*sizeof(Candidate));
                std::vector<U64> visited(in.tasks.size());auto raw=static_cast<const std::uint32_t*>(counts.value.contents);
                for(std::size_t i=0;i<visited.size();++i)visited[i]=raw[i];
                frame_output(request,[&](){print_result("gpu",in,output,visited,elapsed(began),gpu_seconds);});
            }catch(const std::exception& error){frame_output(request,[&](){failure(error);});}
          }
        }
        return 0;
      }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 2;}
    }
}
