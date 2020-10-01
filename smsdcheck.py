#!/usr/bin/python3
############import###############
import os
import time
import smtp2smscfg as cfg
##########config#################
dirs=cfg.dirs #['/var/spool/sms/checked','/var/spool/sms/outgoing']
mdmpath=cfg.mdmpath #'/dev/ttyUSB1'  #Path to modem
mdmcmd=cfg.mdmcmd #'AT+CFUN=1'      #Reboot modem command
smsd=cfg.smsd #'smstools'
maxdelay=cfg.maxdelay #59
##########init###################
mintime = 0
fname = ''
now = 0
delta = 0
##########body###################
for x in dirs:
    ls = os.listdir(x)
    print (ls.__len__())
    for y in ls:
        mtime = round(os.stat(x+ "/" + y).st_mtime, 1)
        now = round(time.time(), 1)
        delta = round(now - mtime, 1)
        print (x + '/' + y + ' --- ' + mtime.__str__(), " --- ", now.__str__(), " --- ", delta.__str__())

        if mintime == 0:
            mintime = mtime
            fname = x + '/' + y
        elif mintime > mtime:
            mintime = mtime
            fname = x + '/' + y
if mintime > 0:
    now = round(time.time(), 1)
    delta = round(now - mintime, 1)

print ("\n" + fname + ' --- ' + mintime.__str__(), " --- ", now.__str__(), " --- ", delta.__str__())

cmd=''
if delta > maxdelay:
    cmd = '/etc/init.d/'+smsd+' stop && echo \''+mdmcmd+'\' >> ' + mdmpath + ' && /etc/init.d/'+smsd+' start'
    print (cmd)
    os.system(cmd)