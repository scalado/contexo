IFS="
"
for func in $(grep -R "def .*(" *|sed -e "s/\ . //g" -e "s/ def/def/g"|cut -d: -f2-1024|sed "s/def //g" |cut -d"(" -f1|grep -v "\." |grep -v ")"|sed "s/\ //g"|grep -v __init__|sort|uniq)
do
    if test $(grep -R "$func" *|wc -l) = 1
    then
        echo $func
    fi
done
