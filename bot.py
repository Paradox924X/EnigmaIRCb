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
    return config.get('enigma-irc-bot', key)

def get_config_bool(key):
    return config.getboolean('enigma-irc-bot', key)

def get_config_int(key):
    return config.getint('enigma-irc-bot', key)

def get_config_float(key):
    return config.getfloat('enigma-irc-bot', key)

def get_config_list(key):
    return get_config(key).split(',')

def is_private(line):
    return line.split(' ')[2] == get_config('nickname')

def get_nick(line):
    return line[1:].split('!')[0]

def is_channel_msg(line):
    return not is_query(line)

def get_channel(line):
    return line.split(' ')[2]

def get_target(line):
    if is_private(line):
        return get_nick(line)
    return get_channel(line)

def extract_command(line):
    global command
    message_parts = line.split(' ')
    if len(message_parts) > 3 and len(message_parts[3]) > 2 and message_parts[3][1] == get_config('command_prefix'):
        command = message_parts[3][2:]
    else:
        command = False
    return command

def write(line, is_silent=False):
    if not is_silent:
        if get_config_bool('show_timestamps'):
            print '[' + str(datetime.datetime.now()) + '] ' + line
        else:
            print line
    s.sendall(line + '\r\n')
    return

def send_privmsg(target, msg, is_silent=False):
    write('PRIVMSG ' + target + ' :' + msg, is_silent)
    return

def send_notice(target, msg, is_silent=False):
    write('NOTICE ' + target + ' :' + msg, is_silent)
    return

def user_identify():
    if get_config('password'):
        write('PRIVMSG ' + get_config('nickserv') + ' IDENTIFY ' + get_config('password'), True)
    return

def user_set_modes(modes):
    write('MODE ' + get_config('nickname') + ' ' + modes)
    return

def user_join_channel(channel):
    write('JOIN ' + channel)
    return

VERSION  = 'EnigmaIRCb v0.1beta'
GREETING = 'Welcome to ' + VERSION + '!'

signal.signal(signal.SIGINT, signal_handler)

config = SafeConfigParser()
config.read('server.cfg')

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
        send_notice(get_nick(line), 'PONG ' + message_parts[4])
    elif len(line.split(':')) > 2 and line.split(':')[2] == 'VERSION':
        send_notice(get_nick(line), 'VERSION ' + VERSION + '')
    elif message_parts[1] == '001':
        user_identify()
        user_set_modes(get_config('usermodes'))
        for channel in get_config_list('channels'):
            user_join_channel(channel)
#### User Commands
    elif extract_command(line):
    	if command == 'version':
            send_privmsg(get_target(line), 'Version: ' + VERSION)

    line = f.readline().rstrip()
else:
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + 'Connection closed'
    else:
        print 'Connection closed'
    s.close()
