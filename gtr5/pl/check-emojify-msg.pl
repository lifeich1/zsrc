#!/usr/bin/env perl
use v5.30;
use strict;
use utf8;
use warnings;

my $txt = qx/head -n 1|emojify/;
if ( $txt =~ /(?:\A|\s):\w+:\s/ ) {
  print "emjify failed: $txt";
  exit 1;
}
print "passed: $txt";
