#!/bin/bash

for file in $(find . -type f |grep "\\.py$")
do
	echo "======$file======"
	pylint -e $file
#	pyflakes $file
#	pychecker $file
done |/bin/grep -v unused >syntax_check.out


