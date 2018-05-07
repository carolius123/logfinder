#!/bin/bash
scp rr.tar $3:$2/elkuser/rr.tar
ssh $3 'tar xvf rr.tar && cd suihf && nice -n 10 ./logfinder && tar czvf result.tar.gz ./data ./logs'
scp $3:$2/elkuser/suihf/result.tar.gz $3.tar.gz
