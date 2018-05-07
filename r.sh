#!/bin/bash
sshpass -p$2 scp rr.tar $1:/elk/elkuser/rr.tar
sshpass -p$2 ssh $1 'tar xvf rr.tar && cd suihf && ./logfinder && tar czvf result.tar.gz ./data ./logs'
sshpass -p$2 scp $1:/elk/elkuser/suihf/result.tar.gz $1.tar.gz
