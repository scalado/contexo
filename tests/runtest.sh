#!/bin/bash
CTX=$PWD/../contexo/cmdline/inplace/ctx.py
OUT=$PWD/out
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_repo/test_output
    rm -f *.a test_repo/*.a test_repo/*.h *.h
    rm -f $OUT
}
fail() {
    cat $OUT
    echo FAIL
    exit 42
}
BCONF=gcc_osx_i386_rel.bc

cp _rspecs/test3.rspec /tmp/
cleanup


echo "build standard"
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail
test -f "bare_hello.a"|| fail
cleanup


echo "buildmod standard"
$CTX buildmod -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail
test -f "bare_hello.a"|| fail
cleanup

echo "build standard with output"
$CTX build -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>$OUT || fail
test -d "test_output"|| fail
cleanup


echo "build in subdirectory without output"
cd test_repo
$CTX build -v ../ -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail

test -f "bare_hello.a"|| fail
cd ..
cleanup

echo "build in subdirectory with output"
cd test_repo
$CTX build -v ../ -b "$BCONF" bare_hello -o test_output 1>/dev/null 2>>$OUT || fail
test -d "test_output" && fail
cd ..
test -d "test_output"|| fail
cleanup

echo "build standard with c++"
$CTX build -b "$BCONF" cpp_hello 1>/dev/null 2>>$OUT || fail
test -f "cpp_hello.a"|| fail
cleanup

echo "buildcomp standard"
$CTX buildcomp -b "$BCONF" hello 1>/dev/null 2>>$OUT|| fail
test -f "hello.a"|| fail
test -f "helloworld.h"|| fail
cleanup

echo "build comp standard"
$CTX build -b "$BCONF" hello.comp 1>/dev/null 2>>$OUT|| fail
test -f "hello.a"|| fail
test -f "helloworld.h"|| fail
cleanup


