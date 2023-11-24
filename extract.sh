#!/bin/bash

dir='loot/ft_fun'
size=`ls $dir | wc -l`
files=`ls $dir`

for i in `seq 1 $size`
do
	for f in $files
	do
		if [[ `cat $dir/$f` == *file$i ]]
		then
			cat $dir/$f
		fi
	done
done
