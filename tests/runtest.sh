#!/bin/bash
CTX=$PWD/../contexo/cmdline/inplace/ctx.py
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_view/test_output
    rm -rf *.a test_view/*.a
}
fail() {
    echo FAIL
    exit 42
}
BCONF=gcc_osx_i386_rel.bc
rm out
cleanup
echo "build standard"
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>out
test -f "bare_hello.a"|| fail
cleanup

echo "build standard with output"
$CTX build -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>out
test -d "test_output"|| fail
cleanup


echo "build in subdirectory without output"
cd test_view
$CTX build -v ../ -b "$BCONF" bare_hello 1>/dev/null 2>>out

test -f "bare_hello.a"|| fail
cd ..
cleanup

echo "build in subdirectory with output"
cd test_view
$CTX build -v ../ -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>out
test -d "test_output" && fail
cd ..
test -d "test_output"|| fail
cleanup

echo "build standard with c++"
$CTX build -b "$BCONF" cpp_hello 1>/dev/null 2>>out
test -f "cpp_hello.a"|| fail
cleanup


