#include <stdio.h>

int main() {
    long i, j, k;
    long res;
    while(i < 5000000) {
        while(j < 5000000) {
            while(k < 5000000) {
                res = i+j*k;
                if (res < 0) printf("plop\n");
                k+=1;
            }
            j+=1;
        }
        i+=1;
    }
    return 0;
}
