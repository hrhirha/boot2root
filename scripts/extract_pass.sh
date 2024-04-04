#!/bin/bash

for i in `seq 1 3`
do
	for f in `ls ft_fun/*.pcap`
	do
		cat $f
		echo " $f"
	done | egrep "file[0-9]{$i}\s" | sort | cut -d ' ' -f2 | xargs cat | egrep -o 'return.*'
done | cut -d "'" -f 2 | tr -d '\n' | sha256sum
