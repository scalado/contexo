#!/bin/bash
CTX=$PWD/../contexo/cmdline/inplace/ctx.py
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_view/test_output
    rm -f out *.a test_view/out test_view/*.a *.h
}
fail() {
    cat out
    echo FAIL
    exit 42
}
BCONF=gcc_osx_i386_rel.bc
rm out

cp _rspecs/test3.rspec /tmp/
cleanup

echo "buildcomp standard"
$CTX buildcomp -b "$BCONF" hello 1>/dev/null 2>>out || fail
test -f "hello.a"|| fail
cleanup


echo "build standard"
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>out || fail
test -f "bare_hello.a"|| fail
cleanup


echo "buildmod standard"
$CTX buildmod -b "$BCONF" bare_hello 1>/dev/null 2>>out || fail
test -f "bare_hello.a"|| fail
cleanup

echo "build standard with output"
$CTX build -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>out || fail
test -d "test_output"|| fail
cleanup


echo "build in subdirectory without output"
cd test_view
$CTX build -v ../ -b "$BCONF" bare_hello 1>/dev/null 2>>out || fail

test -f "bare_hello.a"|| fail
cd ..
cleanup

echo "build in subdirectory with output"
cd test_view
$CTX build -v ../ -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>out || fail
test -d "test_output" && fail
cd ..
test -d "test_output"|| fail
cleanup

echo "build standard with c++"
$CTX build -b "$BCONF" cpp_hello 1>/dev/null 2>>out || fail
test -f "cpp_hello.a"|| fail
cleanup

echo "validate standard"
$CTX view validate 1>/dev/null 2>>out || fail
cleanup

echo "info standard"
$CTX view info  1>/dev/null 2>>out && fail
cleanup


