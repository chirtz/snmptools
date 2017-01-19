# snmpcheck
## Description 
snmpcheck is a set of tools to poll printer information using the SNMP protocol.

## Requirements
- Python 3
 - argparse
 - easysnmp
 - yaml

## Usage
```
printercheck.py [-h] [--host HOST] [--info] [--supplies] [--trays]
                       [--config CONFIG] [--applyrules] [--severity SEVERITY]

Check printers via SNMP.

optional arguments:
  -h, --help            show this help message and exit
  --host HOST, -H HOST
  --info, -i
  --supplies, -s
  --trays, -t
  --config CONFIG, -c CONFIG
  --applyrules, -r
  --severity SEVERITY, -w SEVERITY
```

### Examples
- Show all device info
   ```
$ printercheck.py -H myprinter -ist

Name    : myprinter
Serial  : XXXXXXXXXX
Contact : me@example.com
Location: Building XY, Room 404
Status  : ready
Alerts  : 
Descr   : HP ETHERNET MULTI-ENVIRONMENT,ROM none,JETDIRECT,JD149,EEPROM JDI23e70135,CIDATE 07/11/2016

[ 31.0%]  Black Cartridge 651A HP CE340A (type: tonerCartridge, unit: percent, raw: 31, capacity: 100, class: consumed)
[ 70.0%]  Cyan Cartridge 651A HP CE341A (type: tonerCartridge, unit: percent, raw: 70, capacity: 100, class: consumed)
[ 75.0%]  Magenta Cartridge 651A HP CE343A (type: tonerCartridge, unit: percent, raw: 75, capacity: 100, class: consumed)
[ 73.0%]  Yellow Cartridge 651A HP CE342A (type: tonerCartridge, unit: percent, raw: 73, capacity: 100, class: consumed)
[ 96.0%]  Transfer Kit HP CE516A (type: transferUnit, unit: percent, raw: 96, capacity: 100, class: consumed)
[ 96.0%]  Fuser Kit HP 110V-CE514A, 220V-CE515A (type: fuser, unit: percent, raw: 96, capacity: 100, class: consumed)
[    OK]  Toner Collection Unit HP CE980A (type: cleanerUnit, unit: percent, raw: -3, capacity: unknown, class: filled)
[100.0%]  Document Feeder Kit HP L2718A (type: other, unit: percent, raw: 100, capacity: 100, class: consumed)
[ 99.0%]  Clean Rollers HP None (type: other, unit: percent, raw: 99, capacity: 100, class: other)
[    OK]  Stapler 1 HP C8091A (type: staples, unit: items, raw: -3, capacity: unknown, class: consumed)
[     0]  Tray 1 (type: tray, paper: Any, status: 9, statustext: Non-critical alerts, Unavailable and OnRequest)
[    OK]  Tray 2 (type: tray, paper: Plain, status: 0, statustext: Available and Idle)
[    OK]  Tray 3 (type: tray, paper: Card Glossy, status: 0, statustext: Available and Idle)
[    OK]  Tray 4 (type: tray, paper: Mid Weight, status: 0, statustext: Available and Idle)
[    OK]  Tray 5 (type: tray, paper: Plain, status: 0, statustext: Available and Idle)
```

- Check if rules are violated
 ```
$ printercheck.py -H myprinter -r -c config.yml 
------------------------------
Host: myprinter
[  OK] (Check empty) => Black Cartridge 651A HP CE340A
[  OK] (Check low) => Black Cartridge 651A HP CE340A
[  OK] (Check empty) => Cyan Cartridge 651A HP CE341A
[  OK] (Check low) => Cyan Cartridge 651A HP CE341A
[  OK] (Check empty) => Magenta Cartridge 651A HP CE343A
[  OK] (Check low) => Magenta Cartridge 651A HP CE343A
[  OK] (Check empty) => Yellow Cartridge 651A HP CE342A
[  OK] (Check low) => Yellow Cartridge 651A HP CE342A
[CRIT] (Check empty) => Fuser Kit HP 110V-CE514A, 220V-CE515A
[  OK] (Check low) => Fuser Kit HP 110V-CE514A, 220V-CE515A
 ```
## Further work
The snmplib module provides the possibility to output information in JSON format, which could be used for further processing or for visualization, e.g. in a monitoring web interface:
![alt text](https://github.com/chirtz/snmpcheck/raw/master/screenshot.png)
