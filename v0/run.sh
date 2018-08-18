#!/bin/bash
while getopts "s" arg
do
    case $arg in
        s)
            ETH=$(eval "ifconfig | grep 'eth0'| wc -l")
            if [ "$ETH"  ==  '1' ] ; then
                nohup /usr/local/bin/net_speeder eth0 "ip" >>/root/nohup.out 2>&1 &
            fi
            if [ "$ETH"  ==  '0' ] ; then
                nohup /usr/local/bin/net_speeder venet0 "ip" >>/root/nohup.out 2>&1 &
            fi
            echo 'net_speeder start'
            break
    esac
done


if [[ -e $SSR_CONFPTH ]]; then
    python server.py -c $SSR_CONFPTH
else
    python server.py -p $SERVER_PORT -k $PASSWORD -m $METHOD -O $PROTOCOL -o $OBFS -G $PROTOCOLPARAM
fi

