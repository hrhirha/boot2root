#!/bin/python3

import string

arr = "isrveawhobpnutfg"
s = "giants"

for c in s:
	print("[", end="")
	for a in string.ascii_lowercase:
		if arr[ord(a) & 0xf] == c:
			print(a+"", end="")
	print("]", end="")

# opekma
# opekmq
# opukma
# opukmq
