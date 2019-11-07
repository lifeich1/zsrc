#!/bin/bash

usage() {
    cat << END
usage: $0 [-i <input-file>]
description: read git repos path and do fetch

-i <input-file>     use <input-file> to replace stdin
END
    exit 2
}

frm_stdin=1

args=`getopt hi: $*`

for i in $args; do
    case $i in
        -i)
            frm_stdin=0; input="$2"; shift;
            shift;;
        -h)
            usage;;
    esac
done

do_fetch() {
    if [ -e "$1" ]; then
        echo "[$1]"
        git -C "$1" fetch
    else
        echo "[Warn]: '$1' not exists"
    fi
}

do_loop() {
    while read wdir; do
        a="`echo $wdir | cut -f1 -d '#'`"
        if [ "$a" ]; then
            do_fetch "$a"
        fi
    done
}

if [ $frm_stdin -ne 0 ]; then
    do_loop
else
    cat $input | do_loop
fi
