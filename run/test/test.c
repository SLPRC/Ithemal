#include <stdio.h>
//#include "iacaMarks.h"

int add(int a, int b)
{
    return a+b;
}

int multiply(int a, int b)
{
    return a*b;
}

int main()
{
    //IACA_START
    int a = 0;
    int b = 1;
    int c = add(a,b);
    int d = add(b,c);
    int e = multiply(c,d);
    int f = multiply(d,e);
    //IACA_END
    printf("Hello World!\n%d,%d,%d,%d,%d\n", a,b,c,d,e);
}
