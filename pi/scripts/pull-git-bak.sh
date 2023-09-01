#!/bin/bash

from=vcom:/home/com/var/git.bak.tar
dest=/home/git/backup/

RSYNC=/usr/bin/rsync

$RSYNC -avzh $from $dest
