#include <cstdio>
int main(int c,char**){int*a=new int[4];int v=a[c+4];delete[] a;int x=2147483647;x+=c;std::printf("%d %d\n",v,x);}