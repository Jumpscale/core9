#!/bin/bash
js9_start
ssh -A -i ~/.ssh/main root@localhost -p 2222 'cd /root/gig/code/github/jumpscale/core9; /bin/bash test.sh'
