#!/bin/bash

/usr/bin/python3 -m portr_act -s `cat /home/pi/Code/etc/portr/ka-secret` \
    cli -u `cat /home/pi/Code/etc/portr/ka-url`
