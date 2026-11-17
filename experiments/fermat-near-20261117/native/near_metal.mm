// Native Apple Silicon host for the exact 512-bit Metal interval search.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>
struct Wide { uint32_t limb[16]; };
struct Hit { uint32_t a,b,c; };
static_assert(sizeof(Wide)==64 && sizeof(Hit)==12,"Metal ABI");
void require(bool okay,const char* message) {
    if(!okay) throw std::runtime_error(message);
}
id<MTLDevice> allocated_device(const char* allocation) {
    require(std::string(allocation)=="0","One explicit BOINC device zero is required");
    NSArray<id<MTLDevice>>* devices=MTLCopyAllDevices();
    require(devices.count==1,"The M4 pilot requires exactly one Metal device");
    id<MTLDevice> device=devices[0];
    require([device.name hasPrefix:@"Apple M4"],"This immutable Metal package supports Apple M4 only");
    return device;
}
id<MTLComputePipelineState> pipeline(id<MTLDevice> device,const std::string& shader) {
    std::ifstream source(shader);
    require(bool(source),"Metal shader is missing");
    std::string code((std::istreambuf_iterator<char>(source)),{});
    NSString* text=[[NSString alloc] initWithBytes:code.data() length:code.size() encoding:NSUTF8StringEncoding];
    MTLCompileOptions* options=[MTLCompileOptions new];
    options.fastMathEnabled=NO;
    NSError* error=nil;
    id<MTLLibrary> library=[device newLibraryWithSource:text options:options error:&error];
    if(!library) throw std::runtime_error(error.localizedDescription.UTF8String ?: "Metal compilation failed");
    id<MTLFunction> function=[library newFunctionWithName:@"near_search"];
    require(function!=nil,"Metal function missing");
    id<MTLComputePipelineState> result=[device newComputePipelineStateWithFunction:function error:&error];
    if(!result) throw std::runtime_error(error.localizedDescription.UTF8String ?: "Metal pipeline failed");
    return result;
}
int main(int argc,char** argv) {
    @autoreleasepool {
        try {
            // Probe/compile mode executes no science and makes no M4 acceptance claim.
            if(argc==3 && std::string(argv[1])=="--compile-only") {
                id<MTLDevice> device=MTLCreateSystemDefaultDevice();
                require(device!=nil,"No Metal device for shader compilation");
                pipeline(device,argv[2]);
                std::cout<<"Metal shader compiled on "<<device.name.UTF8String<<'\n';
                return 0;
            }
            require(argc==5,"Expected input, output, allocated device and shader");
            id<MTLDevice> device=allocated_device(argv[3]);
            std::ifstream input(argv[1],std::ios::binary);
            uint32_t header[4]={}; input.read(reinterpret_cast<char*>(header),sizeof(header));
            unsigned first=header[0],last=header[1],capacity=header[3];
            require(bool(input) && header[2]==16 && first>=2 && first<=last && last<=20000
                    && last-first<256 && capacity>0 && capacity<=20000,"Invalid bounded input");
            std::vector<Wide> powers(last+1),radii(last-first+1);
            input.read(reinterpret_cast<char*>(powers.data()),powers.size()*sizeof(Wide));
            input.read(reinterpret_cast<char*>(radii.data()),radii.size()*sizeof(Wide));
            require(bool(input) && input.peek()==std::char_traits<char>::eof(),"Truncated Metal input");
            id<MTLComputePipelineState> state=pipeline(device,argv[4]);
            id<MTLBuffer> p=[device newBufferWithBytes:powers.data() length:powers.size()*sizeof(Wide) options:MTLResourceStorageModeShared];
            id<MTLBuffer> r=[device newBufferWithBytes:radii.data() length:radii.size()*sizeof(Wide) options:MTLResourceStorageModeShared];
            id<MTLBuffer> h=[device newBufferWithLength:capacity*sizeof(Hit) options:MTLResourceStorageModeShared];
            uint32_t zero=0,parameters[3]={first,last,capacity};
            id<MTLBuffer> count=[device newBufferWithBytes:&zero length:sizeof(zero) options:MTLResourceStorageModeShared];
            id<MTLBuffer> error=[device newBufferWithBytes:&zero length:sizeof(zero) options:MTLResourceStorageModeShared];
            id<MTLBuffer> params=[device newBufferWithBytes:parameters length:sizeof(parameters) options:MTLResourceStorageModeShared];
            require(p && r && h && count && error && params,"Metal buffer allocation failed");
            id<MTLCommandQueue> queue=[device newCommandQueue];
            id<MTLCommandBuffer> command=[queue commandBuffer];
            id<MTLComputeCommandEncoder> encoder=[command computeCommandEncoder];
            require(queue && command && encoder,"Metal command allocation failed");
            [encoder setComputePipelineState:state];
            [encoder setBuffer:p offset:0 atIndex:0]; [encoder setBuffer:r offset:0 atIndex:1];
            [encoder setBuffer:h offset:0 atIndex:2]; [encoder setBuffer:count offset:0 atIndex:3];
            [encoder setBuffer:error offset:0 atIndex:4]; [encoder setBuffer:params offset:0 atIndex:5];
            NSUInteger width=std::min<NSUInteger>(128,state.maxTotalThreadsPerThreadgroup);
            require(width>0,"Metal threadgroup unavailable");
            [encoder dispatchThreads:MTLSizeMake(last,last-first+1,1) threadsPerThreadgroup:MTLSizeMake(width,1,1)];
            [encoder endEncoding]; [command commit]; [command waitUntilCompleted];
            if(command.status!=MTLCommandBufferStatusCompleted)
                throw std::runtime_error(command.error.localizedDescription.UTF8String ?: "Metal command failed");
            unsigned n=*static_cast<uint32_t*>(count.contents);
            require(!*static_cast<uint32_t*>(error.contents) && n<=capacity,"Metal arithmetic or candidate buffer overflow");
            Hit* pointer=static_cast<Hit*>(h.contents);
            std::vector<Hit> hits(pointer,pointer+n);
            std::sort(hits.begin(),hits.end(),[](Hit a,Hit b){return a.c!=b.c?a.c<b.c:(a.a!=b.a?a.a<b.a:a.b<b.b);});
            std::ofstream output(argv[2]);
            for(auto hit:hits) output<<hit.a<<' '<<hit.b<<' '<<hit.c<<'\n';
            output.flush();require(bool(output),"Metal output write failed");
            std::cerr<<"Executed exact Metal search on "<<device.name.UTF8String<<", registry "<<device.registryID<<'\n';
            return 0;
        } catch(const std::exception& error) {
            std::cerr<<error.what()<<'\n';return 70;
        }
    }
}
