// Independent complete enumeration: monotone endpoints, GMP powers and residuals.
#include <gmpxx.h>
#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
int main(int argc, char** argv) {
    try {
        if (argc != 6) return 2;
        int n=std::stoi(argv[1]), first=std::stoi(argv[2]), last=std::stoi(argv[3]);
        mpz_class kn(argv[4]), kd(argv[5]);
        if(n<4 || n>32 || first<2 || first>last || last>20000 || kn<=0 || kd<=0) return 3;
        std::vector<mpz_class> powers(last+1);
        for(int x=0;x<=last;++x) mpz_ui_pow_ui(powers[x].get_mpz_t(),x,n);
        unsigned long examined=0,hits=0;
        for(int c=first;c<=last;++c) {
            mpz_class radius;
            mpz_ui_pow_ui(radius.get_mpz_t(),c,n-3); radius=radius*kn/kd;
            int lo=1,hi=1;
            for(int a=c-1;a>=1;--a) {
                ++examined;
                mpz_class target=powers[c]-powers[a], low=target-radius, high=target+radius;
                while(lo<c && powers[lo]<low) ++lo;
                while(hi<c && powers[hi]<=high) ++hi;
                for(int b=std::max(a,lo);b<hi;++b) {
                    mpz_class delta=powers[a]+powers[b]-powers[c];
                    if(delta==0) continue;
                    if(++hits>20000) return 4;
                    std::cout<<"H "<<a<<' '<<b<<' '<<c<<' '<<delta<<'\n';
                }
            }
        }
        std::cout<<"DONE "<<examined<<' '<<hits<<'\n';
    } catch (...) { return 5; }
}
