#!/bin/bash
CTX=$PWD/../inplace/ctx.py
OUT=$PWD/out
cleanup(){
    rm -rf .ctx
    rm -rf test_output
    rm -rf test_repo/test_output
    rm -rf delete_view/delete_repo/delete_modules/delete/inc
    rm -rf delete_view/delete_repo/delete_modules/delete/src
    rm -rf delete_view/.ctx
    rm -rf hello_view/.ctx
    rm -f *.a test_repo/*.a test_repo/*.h *.h freeze.rspec delete_view/*.a hello_view/hello.exe
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
rm -f /tmp/testrepo.svn out
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail

#echo "fail to build if including header in non-included module"
#cd strict_modules
#$CTX build -b "$BCONF" hello.comp
#rm -f hello.a
#cleanup
#cd ..
#exit 0

#echo "fail to build if including header in non-included module"
#cd multiple_headers_view
#$CTX build -b "$BCONF" hello 1>/dev/null 2>>$OUT && fail
#$CTX build -b "$BCONF" goodbye 1>/dev/null 2>>$OUT && fail
#rm -f hello.a goodbye.a
#cleanup
#cd ..
echo "build with sub_bc"
cd sub_bc_view
$CTX build -b "sub_bc_main.bc" hello||fail
#1>/dev/null 2>>$OUT || fail
test -f sub_bc_view/.ctx/obj/Gcc/hello.o ||{ echo "hello.o not compiled"; fail;}
test -f "hello.a"|| fail
cd ..
cleanup
exit 0

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

echo "ctx build exe"
rm -f /tmp/testrepo.svn
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail
cd hello_view
$CTX build -b "$BCONF" hello -exe hello.exe 1>/dev/null 2>>$OUT || fail
test -f "hello.exe"|| fail
cd ..
cleanup

echo "ctx buildcomp --output"
rm -f /tmp/testrepo.svn
ln -s $PWD/testrepo.svn /tmp/testrepo.svn || fail
$CTX buildcomp -b "$BCONF" hello.comp --output test_output 1>/dev/null 2>>$OUT || fail
echo test out dir
test -d test_output || fail
echo test out lib
test -f test_output/hello.a || fail
cleanup


echo "test delete c files"
cp -rf delete_view/delete_repo/delete_modules/delete/src-orig delete_view/delete_repo/delete_modules/delete/src
cp -rf delete_view/delete_repo/delete_modules/delete/inc-orig delete_view/delete_repo/delete_modules/delete/inc
cd delete_view
$CTX buildcomp --bconf $BCONF -delete delete.comp 1>/dev/null 2>>$OUT || fail
test -d delete_repo/delete_modules/delete/src && fail
test -d delete_repo/delete_modules/delete/inc && fail
test -f delete_repo/delete_modules/delete/src/delete.c && fail
test -f delete_repo/delete_modules/delete/delete.h || fail
test -f "delete.a"||fail
cd ..
cleanup

echo "fail on multiple headers"
cd multiple_headers_view
$CTX build -b "$BCONF" wazzup 1>/dev/null 2>>$OUT && fail
rm -f wazzup.a
cleanup
cd ..

echo "continue on multiple headers (legacy compat)"
cd multiple_headers_view
$CTX build -b "$BCONF" --legacy-duplicate-sources wazzup 1>/dev/null 2>>$OUT ||fail
rm -f wazzup.a
cleanup
cd ..


