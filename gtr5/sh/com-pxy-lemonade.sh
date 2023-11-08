#!/bin/bash

/home/fool/bin/lemonade server &
ssh -v -NR 2489:localhost:2489 com
