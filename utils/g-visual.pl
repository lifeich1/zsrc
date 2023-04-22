#!/usr/bin/env perl
use strict;
use utf8;
use v5.24;
use warnings qw/all/;

my @cmd = qw/nvim.appimage/;

if ($ENV{NVIM}) {
    @cmd = (qw/nvr --remote-tab-wait/, qq/+set bufhidden=wipe/);
}
push @cmd, @ARGV;
say "@cmd";

exec @cmd;
