// Exact unsigned 512-bit CUDA interval search. Python prepares exact power tables.
#include "parent_guard.hpp"
#include <cuda_runtime.h>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>
#include <stdexcept>
#include <algorithm>
struct Wide { uint32_t limb[16]; };
struct Hit { uint32_t a,b,c; };
__device__ int compare(const Wide& a,const Wide& b) {
    for(int i=15;i>=0;--i) if(a.limb[i]!=b.limb[i]) return a.limb[i]<b.limb[i]?-1:1;
    return 0;
}
__device__ Wide subtract(const Wide& a,const Wide& b) {
    Wide r; uint64_t borrow=0;
    for(int i=0;i<16;++i) {
        uint64_t sub=uint64_t(b.limb[i])+borrow;
        r.limb[i]=uint32_t(uint64_t(a.limb[i])-sub);
        borrow=uint64_t(a.limb[i])<sub;
    }
    return r;
}
__device__ Wide add(const Wide& a,const Wide& b,unsigned* error) {
    Wide r; uint64_t carry=0;
    for(int i=0;i<16;++i) {
        uint64_t sum=uint64_t(a.limb[i])+b.limb[i]+carry;
        r.limb[i]=uint32_t(sum); carry=sum>>32;
    }
    if(carry) atomicExch(error,1);
    return r;
}
__global__ void search(const Wide* powers,const Wide* radii,unsigned first,unsigned last,
                       Hit* hits,unsigned capacity,unsigned* count,unsigned* error) {
    unsigned c=first+blockIdx.y,a=blockIdx.x*blockDim.x+threadIdx.x+1;
    if(c>last || a>=c) return;
    Wide target=subtract(powers[c],powers[a]),zero{};
    Wide low=compare(target,radii[c-first])<0?zero:subtract(target,radii[c-first]);
    Wide high=add(target,radii[c-first],error);
    unsigned lo=a,hi=c;
    while(lo<hi) { unsigned mid=lo+(hi-lo)/2; if(compare(powers[mid],low)<0) lo=mid+1; else hi=mid; }
    unsigned begin=lo; hi=c;
    while(lo<hi) { unsigned mid=lo+(hi-lo)/2; if(compare(powers[mid],high)<=0) lo=mid+1; else hi=mid; }
    for(unsigned b=begin;b<lo;++b) {
        unsigned index=atomicAdd(count,1);
        if(index<capacity) hits[index]=Hit{a,b,c};
    }
}
void checked(cudaError_t status) {
    if(status!=cudaSuccess) throw std::runtime_error(cudaGetErrorString(status));
}
int main(int argc,char** argv) {
    try {
        protect_parent();
        if(argc!=3) return 2;
        std::ifstream input(argv[1],std::ios::binary);
        uint32_t header[4]; input.read(reinterpret_cast<char*>(header),sizeof(header));
        unsigned first=header[0],last=header[1],capacity=header[3];
        if(!input || header[2]!=16 || first<2 || first>last || last>20000 || last-first>=256 || !capacity || capacity>20000) return 3;
        std::vector<Wide> p(last+1),r(last-first+1);
        input.read(reinterpret_cast<char*>(p.data()),p.size()*sizeof(Wide));
        input.read(reinterpret_cast<char*>(r.data()),r.size()*sizeof(Wide));
        if(!input || input.peek()!=std::char_traits<char>::eof()) return 4;
        checked(cudaSetDevice(0)); // visibility is restricted to BOINC's allocated device
        Wide *dp,*dr; Hit* dh; unsigned *dc,*de;
        checked(cudaMalloc(&dp,p.size()*sizeof(Wide))); checked(cudaMalloc(&dr,r.size()*sizeof(Wide)));
        checked(cudaMalloc(&dh,capacity*sizeof(Hit))); checked(cudaMalloc(&dc,sizeof(unsigned))); checked(cudaMalloc(&de,sizeof(unsigned)));
        checked(cudaMemcpy(dp,p.data(),p.size()*sizeof(Wide),cudaMemcpyHostToDevice));
        checked(cudaMemcpy(dr,r.data(),r.size()*sizeof(Wide),cudaMemcpyHostToDevice));
        checked(cudaMemset(dc,0,sizeof(unsigned))); checked(cudaMemset(de,0,sizeof(unsigned)));
        search<<<dim3((last+127)/128,last-first+1),128>>>(dp,dr,first,last,dh,capacity,dc,de);
        checked(cudaGetLastError()); checked(cudaDeviceSynchronize());
        unsigned count,error; checked(cudaMemcpy(&count,dc,sizeof(count),cudaMemcpyDeviceToHost));
        checked(cudaMemcpy(&error,de,sizeof(error),cudaMemcpyDeviceToHost));
        if(error || count>capacity) throw std::runtime_error("Arithmetic or candidate buffer overflow");
        std::vector<Hit> hits(count); checked(cudaMemcpy(hits.data(),dh,count*sizeof(Hit),cudaMemcpyDeviceToHost));
        std::sort(hits.begin(),hits.end(),[](Hit a,Hit b){return a.c!=b.c?a.c<b.c:(a.a!=b.a?a.a<b.a:a.b<b.b);});
        std::ofstream output(argv[2]); for(auto h:hits) output<<h.a<<' '<<h.b<<' '<<h.c<<'\n';
        if(!output) throw std::runtime_error("Output write failed");
        checked(cudaFree(dp));checked(cudaFree(dr));checked(cudaFree(dh));checked(cudaFree(dc));checked(cudaFree(de));
        return 0;
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 70; }
}
