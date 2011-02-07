#!/bin/bash
CTX=$PWD/../contexo/cmdline/inplace/ctx.py
OUT=$PWD/out
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_repo/test_output
    rm -rf delete_view/delete_repo/delete_modules/delete/inc
    rm -rf delete_view/delete_repo/delete_modules/delete/src
    rm -rf delete_view/.ctx
    rm -f *.a test_repo/*.a test_repo/*.h *.h freeze.rspec delete_view/*.a
    rm -f $OUT
}
fail() {
    cat $OUT
    echo FAIL
    exit 42
}

BCONF=gcc.bc
#BCONF=gcc_osx_i386_rel.bc
echo "creating dummy repository"
rm -f /tmp/testrepo.svn
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail

echo "build standard"
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail
test -f "bare_hello.a"|| fail
cleanup

echo "testing clean -a after build"
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail
test -f "bare_hello.a"|| fail
$CTX clean -a  1>/dev/null 2>>$OUT || fail
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

echo "test disconnected operation"
rm /tmp/testrepo.svn
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail
$CTX view update 1>/dev/null 2>>$OUT || fail
rm /tmp/testrepo.svn
$CTX build -b "$BCONF" bare_hello 1>/dev/null 2>>$OUT || fail
test -f "bare_hello.a"|| fail
cleanup

echo "ctx freeze"
rm -f /tmp/testrepo.svn
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail
$CTX freeze -o freeze.rspec 1>/dev/null 2>>$OUT || fail
test -f "freeze.rspec"|| fail
cleanup

echo "test delete c files"
cp -rf delete_view/delete_repo/delete_modules/delete/src-orig delete_view/delete_repo/delete_modules/delete/src
cp -rf delete_view/delete_repo/delete_modules/delete/inc-orig delete_view/delete_repo/delete_modules/delete/inc
cd delete_view
$CTX buildcomp --bconf $BCONF -delete delete.comp 1>/dev/null 2>>$OUT || fail
exit 1
test -d delete_repo/delete_modules/delete/src && fail
test -d delete_repo/delete_modules/delete/inc && fail
test -f delete_repo/delete_modules/delete/src/delete.c || fail
test -f delete_repo/delete_modules/delete/delete.h || fail
test -f "delete.a"||fail
cd ..
cleanup

