#include <stdio.h>

int main() {
    long j=0, k=0;
    long res;
    while(j < 500) {
        k = 0;
        while(k < 5000000) {
            res = j*k;
            if (res < 0) printf("plop\n");
            k+=1;
        }
        j+=1;
    }
    return 0;
}
