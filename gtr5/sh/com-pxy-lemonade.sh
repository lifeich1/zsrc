#!/bin/bash

/home/fool/bin/lemonade server &
ssh -NR 2489:localhost:2489 com
