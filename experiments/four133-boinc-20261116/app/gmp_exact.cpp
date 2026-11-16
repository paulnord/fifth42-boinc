// Independent final signed 133rd-power arithmetic. No search-engine headers.
#include <gmpxx.h>
#include <iostream>
int main() {
    long a,b,c,d;
    unsigned count=0;
    while(std::cin>>a>>b>>c>>d) {
        if(++count>20000) return 2;
        mpz_class total=-42;
        for(long x : {a,b,c,d}) {
            if(x < -20000000 || x > 20000000) return 3;
            mpz_class base=x,power;
            mpz_pow_ui(power.get_mpz_t(),base.get_mpz_t(),133);
            total+=power;
        }
        std::cout<<total<<'\n';
    }
    return std::cin.eof()?0:4;
}
