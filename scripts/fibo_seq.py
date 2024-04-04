import sys

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} NUM")
    exit(1)
n = int(sys.argv[1])
fibo = [1,1]
while True:
    f2 = fibo[len(fibo)-1]
    f1 = fibo[len(fibo)-2]
    fsum = f1 + f2
    fibo.append(f1 + f2)
    if fsum == n:
        break

print(f'{len(fibo)-1}', end="")
#for i in fibo:
#    print(f'{i} ', end="")
