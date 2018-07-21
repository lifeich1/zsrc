#!/bin/bash

if [[ -e $SSR_CONFPTH ]]; then
    python server.py -c $SSR_CONFPTH
else
    python server.py -p $SERVER_PORT -k $PASSWORD -m $METHOD -O $PROTOCOL -o $OBFS -G $PROTOCOLPARAM
fi

