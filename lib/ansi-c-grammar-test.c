/*
 * This file is for straightforward verification that
 * everything in the ansi-c.grammar gets parsed and
 * converted by c.lc.
 *
 */


// declaration rule
static int foo;
struct hello;

// most of the other tests
// verify that declaration specifiers
// work, so we skip them.

// declarators, with and without initializers.
static int a,b=1,c;

// different forms of declarators
// parameters
void world(
        void (*)(),
        int*const x,
        void *bar[], ...);

// abstract declarators use the same
// rules, so we can verify they parse
// as well.

// initializer with list
static int faa[] = {1, 2, 3};

// structures, unions and enumerators
struct g {
    float x;
};

enum f {
    gugx,
    grhx = 3,
    rgxh
};

// definitions
void z() {
repeat:
    if (y) {
    }
    switch(x) {
        case A:
            break;
        default:
            return 1;
    }
    while (0) {
        continue;
    }
    for(1; 0; 3) {
        return;
    }
    goto repeat;
}
