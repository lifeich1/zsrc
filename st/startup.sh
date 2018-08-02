#!/bin/bash

docker run -d --name sync \
    -p 8384:8384 \
    -p 22000:22000 \
    -p 21027:21027/udp \
    -v ~/Sync:/root/Sync \
    lintd/sync
