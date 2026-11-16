#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>
using u64=uint64_t; using u128=__uint128_t;
constexpr int Q=1597,E=133,D=4206930;
u64 power(u64 a,int e,u64 m){u64 r=1;for(;e;e>>=1,a=u64(u128(a)*a%m))if(e&1)r=u64(u128(r)*a%m);return r;}
u64 sub(u64 a,u64 b,u64 m){return a>=b?a-b:a+m-b;}
u64 add(u64 a,u64 b,u64 m){u64 s=a+b;return s>=m?s-m:s;}
int modq(int a){a%=Q;return a<0?a+Q:a;}
int label(u64 p,int sign){if(sign<0)p=p?Q-p:0;return p==1?0:p==325?1:p==1312?2:-1;}
int type(int a,int b){if(a<0||b<0)return -1;if(a>b)std::swap(a,b);return a==0?(b==0?0:b==1?1:2):(a==1&&b==2?3:-1);}
int maxgap(int B,int S,int sign,bool pair22){
 if(!pair22)return std::max(0,std::min({(2*B-(sign>0))/135,(2*S-2-(sign>0))/131,(2*B-S)/3}));
 int low=0,high=B; u64 limit=u64(S)*B-(sign>0);
 while(low<high){int mid=low+(high-low+1)/2;if(66ULL*mid*mid<=limit)low=mid;else high=mid-1;}
 return std::max(0,std::min(low,(B-S-1)/2));
}
struct Entry{u64 value;int base;bool operator<(const Entry&o)const{return value<o.value||(value==o.value&&base<o.base);}};
int main(int argc,char**argv){try{
 if(argc!=12)throw std::runtime_error("usage: search 22|31 B old modulus S sign start end source_sha production|synthetic candidate_limit");
 std::string pattern=argv[1],sha=argv[9],mode=argv[10]; bool pair22=pattern=="22",test=mode=="synthetic";
 int B=std::stoi(argv[2]),old=std::stoi(argv[3]),S=std::stoi(argv[5]),sign=std::stoi(argv[6]),start=std::stoi(argv[7]),end=std::stoi(argv[8]);u64 m=std::stoull(argv[4]),cap=std::stoull(argv[11]);
 if((!pair22&&pattern!="31")||(!test&&mode!="production")||B<44||B>20000000||old<0||old>=B||S<42||S>2*B+42||(sign!=1&&sign!=-1)||m<=42||m>=(u64(1)<<61)||sha.size()!=64||!cap)throw std::runtime_error("unsupported configuration");
 if(!test&&(old!=4000000||(sign*S-42)%D||sign*S < -2*B||sign*S>2*B+42||(m!=2305843009213693921ULL&&m!=2305843009213693951ULL)))throw std::runtime_error("invalid production case");
 int H=maxgap(B,S,sign,pair22);if(start<1||end>H||start>end)throw std::runtime_error("invalid gap interval");
#ifndef __SANITIZE_ADDRESS__
 rlimit lim{1024ULL*1024*1024,1024ULL*1024*1024};if(setrlimit(RLIMIT_AS,&lim))throw std::runtime_error("memory limit failed");
#endif
 auto t0=std::chrono::steady_clock::now();std::vector<u64> p(B+1);for(int x=1;x<=B;x++)p[x]=power(x,E,m);
 double setup=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
 std::array<int,Q>P,N;for(int r=0;r<Q;r++){u64 x=power(r,E,Q);P[r]=label(x,sign);N[r]=label(x?Q-x:0,sign);}
 std::cout<<"START version=2 pattern="<<pattern<<" bound="<<B<<" previous_bound="<<old<<" modulus="<<m<<" normalized_sum="<<S<<" sign="<<sign<<" normalized_target="<<42*sign<<" max_gap="<<H<<" start="<<start<<" end="<<end<<" test_mode="<<test<<" source_sha="<<sha<<" setup_seconds="<<setup<<std::endl;
 u64 leftTotal=0,rightTotal=0,rawTotal=0,canonicalTotal=0,distinctTotal=0;
 for(int h=start;h<=end;h++){
  std::array<std::vector<Entry>,4>L,R;u64 nL=0,nR=0,raw=0,canonical=0,distinct=0;
  int leftLow=pair22?1:(S+h+1)/2,leftHigh=pair22?B-2*h-S:std::min(B-h,S+h-1);
  int rightLow=std::max(pair22?S+h+1:(S+h+1)/2,old-h+1),rightHigh=B-h;
  for(int r=0;r<Q;r++){
   int lt=pair22?type(P[modq(r+h+S)],N[r]):type(P[modq(S+h-r)],P[r]);int rt=type(P[r],N[modq(r+h)]);
   if(lt>=0)for(int x=leftLow+modq(r-modq(leftLow));x<=leftHigh;x+=Q){u64 key=pair22?sub(p[x+h+S],p[x],m):add(p[S+h-x],p[x],m);L[lt].push_back({key,x});nL++;}
   if(rt>=0)for(int x=rightLow+modq(r-modq(rightLow));x<=rightHigh;x+=Q){u64 key=sub(p[x+h],p[x],m);key=sign<0?sub(key,42,m):add(key,42,m);R[3-rt].push_back({key,x});nR++;}
  }
  for(int z=0;z<4;z++){
   auto&l=L[z];auto&r=R[z];std::sort(l.begin(),l.end());std::sort(r.begin(),r.end());size_t i=0,j=0;
   while(i<l.size()&&j<r.size()){
    if(l[i].value<r[j].value){i++;continue;}if(r[j].value<l[i].value){j++;continue;}
    size_t ie=i+1,je=j+1;while(ie<l.size()&&l[ie].value==l[i].value)ie++;while(je<r.size()&&r[je].value==r[j].value)je++;
    for(size_t x=i;x<ie;x++)for(size_t y=j;y<je;y++){
     raw++;int a,b,c,d;
     if(pair22){c=l[x].base;a=c+h+S;b=r[y].base;d=b+h;if(a>b)continue;}
     else{b=l[x].base;a=S+h-b;c=r[y].base;d=c+h;if(b>c)continue;}
     if(canonicalTotal+canonical>=cap)throw std::runtime_error("candidate cap reached; incomplete chunk");
     canonical++;bool distinctBase=pair22?a<b:(a<b&&b<c);distinct+=distinctBase;
     if(pair22){c=-c;d=-d;}else d=-d;a*=sign;b*=sign;c*=sign;d*=sign;
     std::cout<<"CANDIDATE h="<<h<<" a="<<a<<" b="<<b<<" c="<<c<<" d="<<d<<" distinct="<<distinctBase<<" residue="<<l[x].value<<"\n";
    }i=ie;j=je;
   }
  }
  leftTotal+=nL;rightTotal+=nR;rawTotal+=raw;canonicalTotal+=canonical;distinctTotal+=distinct;rusage ru{};getrusage(RUSAGE_SELF,&ru);
  std::cout<<"CHECKPOINT h="<<h<<" left="<<nL<<" right="<<nR<<" raw="<<raw<<" canonical="<<canonical<<" distinct="<<distinct<<" wall="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count()<<" rss_kib="<<ru.ru_maxrss<<std::endl;
 }
 std::cout<<"CHUNK_DONE pattern="<<pattern<<" bound="<<B<<" previous_bound="<<old<<" modulus="<<m<<" normalized_sum="<<S<<" sign="<<sign<<" start="<<start<<" end="<<end<<" left="<<leftTotal<<" right="<<rightTotal<<" raw="<<rawTotal<<" canonical="<<canonicalTotal<<" distinct="<<distinctTotal<<std::endl;
 return 0;
}catch(const std::exception&e){std::cerr<<"ERROR "<<e.what()<<std::endl;return 2;}}
