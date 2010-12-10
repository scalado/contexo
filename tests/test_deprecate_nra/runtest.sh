#!/bin/bash
test_fail () {
    echo FAIL
    exit 8
}


rm -rf bare_hello.a
ctx build -b gcc.bc bare_hello
test -f "bare_hello.a" || test_fail
rm -rf bare_hello.a
cd test_view
ctx build -v ../ -b gcc.bc bare_hello
test -f "bare_hello.a" || test_fail
rm -rf test_output
cd ..
ctx build -b gcc.bc bare_hello -o test_output
test -d "test_output" || test_fail
rm -rf test_output
cd test_view
ctx build -v ../ -b gcc.bc bare_hello -o test_output
cd ..
test -d "test_output" || test_fail

