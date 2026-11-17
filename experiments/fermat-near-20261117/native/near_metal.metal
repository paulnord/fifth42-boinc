#include <metal_stdlib>
using namespace metal;
struct Wide { uint limb[16]; };
struct Hit { uint a,b,c; };

int wide_compare(Wide a, Wide b) {
    for (int i=15;i>=0;--i) {
        if (a.limb[i]!=b.limb[i]) return a.limb[i]<b.limb[i]?-1:1;
    }
    return 0;
}
Wide wide_subtract(Wide a, Wide b) {
    Wide r;
    uint borrow=0;
    for (uint i=0;i<16;++i) {
        uint first=a.limb[i]-b.limb[i];
        uint b1=a.limb[i]<b.limb[i];
        r.limb[i]=first-borrow;
        borrow=b1 | uint(first<borrow);
    }
    return r;
}
Wide wide_add(Wide a, Wide b, device atomic_uint* error) {
    Wide r;
    uint carry=0;
    for (uint i=0;i<16;++i) {
        uint first=a.limb[i]+b.limb[i];
        uint c1=first<a.limb[i];
        r.limb[i]=first+carry;
        carry=c1 | uint(r.limb[i]<first);
    }
    if(carry) atomic_store_explicit(error,1,memory_order_relaxed);
    return r;
}
kernel void near_search(device const Wide* powers [[buffer(0)]],
                        device const Wide* radii [[buffer(1)]],
                        device Hit* hits [[buffer(2)]],
                        device atomic_uint* count [[buffer(3)]],
                        device atomic_uint* error [[buffer(4)]],
                        constant uint* params [[buffer(5)]],
                        uint2 position [[thread_position_in_grid]]) {
    uint first=params[0],last=params[1],capacity=params[2];
    uint c=first+position.y,a=position.x+1;
    if(c>last || a>=c) return;
    Wide target=wide_subtract(powers[c],powers[a]);
    Wide radius=radii[c-first];
    Wide zero={};
    Wide low=wide_compare(target,radius)<0?zero:wide_subtract(target,radius);
    Wide high=wide_add(target,radius,error);
    uint lo=a,hi=c;
    while(lo<hi) {
        uint mid=lo+(hi-lo)/2;
        if(wide_compare(powers[mid],low)<0) lo=mid+1; else hi=mid;
    }
    uint begin=lo;
    hi=c;
    while(lo<hi) {
        uint mid=lo+(hi-lo)/2;
        if(wide_compare(powers[mid],high)<=0) lo=mid+1; else hi=mid;
    }
    for(uint b=begin;b<lo;++b) {
        uint index=atomic_fetch_add_explicit(count,1,memory_order_relaxed);
        if(index<capacity) hits[index]=Hit{a,b,c};
    }
}
