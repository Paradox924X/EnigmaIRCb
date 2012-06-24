#!/usr/bin/python
# Author: Nikunj Mehta

from ConfigParser import SafeConfigParser
import datetime
import signal
import socket
import ssl
import string
import sys

def signal_handler(signal, frame):
    if s:
        write('QUIT ' + VERSION)
        s.close()
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + 'Exiting...'
    else:
        print 'Exiting...'
    sys.exit(0)

def get_config(key):
    return parser.get('enigma-irc-bot', key)

def get_config_bool(key):
    return parser.getboolean('enigma-irc-bot', key)

def get_config_int(key):
    return parser.getint('enigma-irc-bot', key)

def get_config_float(key):
    return parser.getfloat('enigma-irc-bot', key)

def get_config_list(key):
    return get_config(key).split(',')

def write(msg):
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + msg
    else:
        print msg
    write_s(msg)
    return

def write_s(msg):
    s.sendall(msg + '\r\n')
    return

def is_private(msg):
    return msg.split(' ')[2] == get_config('nickname')

def get_nick(msg):
    return line[1:].split('!')[0]

def is_channel_msg(msg):
    return -is_query(msg)

def get_channel(msg):
    return msg.split(' ')[2]

def get_target(msg):
    if is_private(msg):
        return get_nick(msg)
    return get_channel(msg)

VERSION  = 'EnigmaIRCb v0.1beta'
GREETING = 'Welcome to ' + VERSION + '!'

signal.signal(signal.SIGINT, signal_handler)

parser = SafeConfigParser()
parser.read('server.cfg')
if get_config_bool('show_timestamps'):
    print '[' + str(datetime.datetime.now()) + '] ' + '='*len(GREETING)
    print '[' + str(datetime.datetime.now()) + '] ' + GREETING
    print '[' + str(datetime.datetime.now()) + '] ' + '='*len(GREETING)
else:
    print '='*len(GREETING)
    print GREETING
    print '='*len(GREETING)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((get_config('hostname'), get_config_int('port')))

if get_config_bool('use_ssl'):
    s = ssl.wrap_socket(s)

f = s.makefile()

if s is None:
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + 'Failed to connect to host (' + get_config('hostname') + ')'
    else:
        print 'Failed to connect to host (' + get_config('hostname') + ')'
    sys.exit(1)

#### Registration
write('NICK ' + get_config('nickname'))
write('USER ' + get_config('nickname') + ' ' + get_config('nickname') + ' ' + get_config('nickname') + ' : ' + get_config('realname'))

line = f.readline().rstrip()
while line:
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + line
    else:
        print line
    message_parts = line.split(' ')
    if message_parts[0] == 'PING':
        write('PONG ' + message_parts[1])
    elif len(message_parts) > 4 and message_parts[3] == ':PING':
        write('NOTICE ' + get_nick(line) + ' :PONG ' + message_parts[4])
    elif len(line.split(':')) > 2 and line.split(':')[2] == 'VERSION':
        write('NOTICE ' + get_nick(line) + ' :VERSION ' + VERSION + '')
    elif message_parts[1] == '001':
        write('MODE ' + get_config('nickname') + ' ' + get_config('usermodes'))
        for channel in get_config_list('channels'):
            write('JOIN ' + channel)
    line = f.readline().rstrip()
else:
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + 'Connection closed'
    else:
        print 'Connection closed'
    s.close()
