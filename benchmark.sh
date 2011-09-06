#!/bin/sh
before="$(date +%s)"
ack -a a /usr/include/ | dd of=/dev/null
after="$(date +%s)"
elapsed_seconds="$(expr $after - $before)"
echo "\n*** Elapsed time for ack: $elapsed_seconds ***\n"

before="$(date +%s)"
grep -R a . /usr/include/ | dd of=/dev/null
after="$(date +%s)"
elapsed_seconds="$(expr $after - $before)"
echo "\n*** Elapsed time for grep: $elapsed_seconds ***\n"

before="$(date +%s)"
lk --num-processes=10 a /usr/include/ | dd of=/dev/null
after="$(date +%s)"
elapsed_seconds="$(expr $after - $before)"
echo "\n*** Elapsed time for lk: $elapsed_seconds ***\n"

before="$(date +%s)"
pypy `which lk` --num-processes=10 a /usr/include/ | dd of=/dev/null
after="$(date +%s)"
elapsed_seconds="$(expr $after - $before)"
echo "\n*** Elapsed time for lk in pypy: $elapsed_seconds ***\n"
