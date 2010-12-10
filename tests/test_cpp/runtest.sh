#!/bin/bash
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_view/test_output
    rm -rf *.a test_view/*.a
}
fail() {
    cleanup
    echo FAIL
    exit 42
}
BCONF=gcc_osx_i386_rel.bc
echo "build standard"
ctx build -b "$BCONF" bare_hello 2>/dev/null
test -f "bare_hello.a"|| fail
cleanup

echo "build standard with output"
ctx build -b "$BCONF" bare_hello -o test_output 2>/dev/null
test -d "test_output"|| fail
cleanup


echo "build in subdirectory without output"
cd test_view
ctx build -v ../ -b "$BCONF" bare_hello 2>/dev/null
test -f "bare_hello.a"|| fail
cd ..
cleanup

echo "build in subdirectory with output"
cd test_view
ctx build -v ../ -b "$BCONF" bare_hello -o test_output 2>/dev/null
test -d "test_output" && fail
cd ..
test -d "test_output"|| fail
cleanup

echo "build standard"
ctx build -b "$BCONF" bjarne 2>/dev/null
test -f "bjarne.a"|| fail
cleanup


