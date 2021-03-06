#!/usr/bin/python3

import smtpd
import asyncore
import datetime
import re
import os
import pwd
import time
import email
import subprocess
import smtp2smscfg as cfg

port=cfg.port #25                      #Listening port
addr=cfg.addr #'0.0.0.0'               #Listening address
app=cfg.app #'/usr/bin/sendsms'        #Path to sendsms script
uid=cfg.uid #'smsd'                    #Effective UID
mdmrmbss=cfg.mdmrmbss #0               #Reboot modem before sending sms (it needs uid=root): 0=no, 1=yes
mdmrebootdelay=cfg.mdmrebootdelay #3   #After reboot delay in seconds
mdmpath=cfg.mdmpath #'/dev/ttyUSB1'    #Path to modem
mdmcmd=cfg.mdmcmd #'AT+CFUN=1'         #Reboot modem command

domain=cfg.domain
subs=cfg.subs
maxlength = cfg.maxlength


class CustomSMTPServer(smtpd.SMTPServer):

    def process_message(self, peer, mailfrom, rcpttos, data, mail_options=None, rcpt_options=None):
        echo('New message recieved. Processing...')
        sub,dom=rcpttos[0].split('@')
#        body = "\n\n".join(data.split("\n\n")[1:])
#        header={}
#        for x in re.sub(r'\n\s+',r' ',data.split("\n\n")[0]).split("\n"):
#            header[x.split(':',1)[0].strip()] = x.split(':',1)[1].strip()
#        subj = header['Subject'].replace('_',' ')
#        subj = re.sub(r'(=([A-Fa-f0-9]){2}){2}',cb2utf8,subj)
#        subj = re.sub(r'=([A-Fa-f0-9]){2}',cb2utf8,subj)
#        subj = subj.replace('=?UTF-8?Q?','').replace(r'?=','')
        msg = email.message_from_string(data.decode())
        subj = decode_subject(msg.get('Subject'))
#################################
        message = ''
        if msg.is_multipart():
            for payload in msg.get_payload():
                content_type = payload.get_content_type()
                if content_type == 'text/plain':
                    message = decode_payload(payload)
                    break
                elif content_type == 'text/html':
                    message = decode_payload(payload)
        else:
            message = decode_payload(msg)
#################################
        body = subj  + ': ' + message

        if dom != domain:
            echo('Wrong domain!')
            return

        if not(sub in subs):
            echo('Unknown error!')
            return

        subtype=type(subs[sub])
        if subtype != str and subtype != list:
            echo('Internal error! Wrong subscriber type.')
            return

        if subtype == str:
            sub = re.sub(r'[^\d]',r'',subs[sub])
        if subtype == list:
            tsubs=[]
            for x in subs[sub]:
                if type(subs[x]) == str:
                    subs[x]=re.sub(r'[^\d]',r'',subs[x])
                    if len(subs[x])==11:
                        tsubs.append(subs[x])
            sub=" ".join(tsubs)
        if len(sub)<11:
            echo('Internal error! Wrong subscriber\'s number(s).')
            return

        #body=re.sub(r'([`\"$\\])',r'\\\1',body)
        body=re.sub(r'\\',r"\\\\",body)
        body=re.sub(r'([\'])',r"'\\\1'",body)
        body=re.sub(r'\n|=0A|=0a',r" ",body)
        body=body[:maxlength]

        #cmd='echo \''+datetime.datetime.now().strftime("%d.%m.%Y, %H:%M:%S")+' New message for: '+sub+'. Message text: "'+body.strip()+'"\''
        cmd=app+' \''+sub+'\' \''+body.strip()+'\' > /dev/null'
        rebootmodem()
        echo(cmd)
        os.system(cmd)
        return

def cb2utf8(o):
    barr = str(o.group())[1:].split('=')
    i=0; x=''
    for x in barr:
        barr[i]=int(x,base=16)
        i += 1
    return str(bytearray(barr))

def echo(m):
    message = datetime.datetime.now().__str__() + " " + m
    print (message)
    f = open(cfg.log,"a")
    f.write(message + "\n")
    f.close()
    return

def rebootmodem():
    if mdmrmbss:
        os.system('echo \'' + mdmcmd + '\' >> ' + mdmpath)
        time.sleep(mdmrebootdelay)
    return

def decode_payload(payload=None):
    message = ''
    content_type = ''
    cte = ''
    
    if type(payload) != None:
        content_type = payload.get_content_type()
        cte = payload.get('Content-Transfer-Encoding').lower()
        
    if content_type == 'text/plain' or content_type == 'text/html':
        if cte == 'base64' or cte == 'quoted-printable':
            message = payload.get_payload(None, True).decode()
        elif cte == '8bit' or cte == '7bit':
            message = payload.get_payload()
            
    if content_type == 'text/html':
        message = re.sub(r'<br>','\n',message)
        message = re.sub('<[^>]*>','',message)
        
    return message

def decode_subject(subject=''):
    res = ''
    content = None
    if type(subject) == str:
        content = email.header.decode_header(subject)
        print('here...')
    if type(content) == list and type(content[0]) == tuple:
        if type(content[0][0]) == bytes:
            res = content[0][0].decode()
        elif type(content[0][0]) == str:
            res = content[0][0]
    return res

######################START HERE#########################
scrname = __file__.split('/')[-1]
scrpath = os.path.abspath(__file__)

if os.getuid()>0:
    print("This program needs superuser rights to start.")
    exit(1)

if os.path.exists(cfg.log):
    cfg.donothing()
else:
    echo("New log file created.")
    os.chown(cfg.log, pwd.getpwnam(uid).pw_uid, pwd.getpwnam(uid).pw_gid)

PIPE = subprocess.PIPE
p = subprocess.Popen(cfg.pidof+' '+cfg.python+' '+scrpath, shell=True, stdout=PIPE, close_fds=True, cwd='.')
pid = p.stdout.read().strip()
pid = pid.split(b' ')

if len(pid) == 1:
    #echo ('Starting... PID is:' + b' '.join(pid).decode())
    echo ('Starting... PID is:' + os.getpid().__str__())
else:
    pid = pid[1:]
    print ('Another instance exists: ' + b' '.join(pid).decode() + '. My PID is ' + os.getpid().__str__())
    exit(1)

server = CustomSMTPServer((addr, port), None)
echo('Binding port 25 ok.')

os.setgid(pwd.getpwnam(uid).pw_gid)
os.setuid(pwd.getpwnam(uid).pw_uid)

echo('Setting up new uid:gid for the process: ' + os.getuid().__str__() + ":" + os.getgid().__str__())
echo('smtp2sms is ready!')

asyncore.loop()
