#!/usr/bin/python
# Author: Nikunj Mehta

from ConfigParser import RawConfigParser
import datetime
import re
import signal
import socket
import ssl
import string
import sys

####

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

####

def is_private_msg(line):
    return is_my_nick(line.split(' ')[2])

def is_channel_msg(line):
    return not is_private_msg(line)

def is_my_nick(nick):
    return nick is not None and nick == get_config('nickname')

####

def extract_nick(line):
    return line[1:].split('!')[0]

def extract_channel(line):
    return line.split(' ')[2].lower()

def extract_target(line):
    if is_private_msg(line):
        return extract_nick(line)
    return extract_channel(line)

def extract_reply_code(line):
    global reply_code
    reply_code = False
    message_parts = line.split(' ')
    if len(message_parts) > 1 and re.search('^\d{3}$', message_parts[1]):
        reply_code = int(message_parts[1])
    return reply_code

def extract_command(line):
    global command
    command = False
    message_parts = line.split(' ')
    if len(message_parts) > 3 and len(message_parts[3]) > 2 and message_parts[3][1] == get_config('command_prefix'):
        command = message_parts[3][2:]
    return command

####

def send_privmsg(target, msg, is_silent=False):
    write('PRIVMSG ' + target + ' :' + msg, is_silent)
    return

def send_notice(target, msg, is_silent=False):
    write('NOTICE ' + target + ' :' + msg, is_silent)
    return

####

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

####

def print_out(line):
    if get_config_bool('show_timestamps'):
        print '[' + str(datetime.datetime.now()) + '] ' + line
    else:
        print line
    return

def write(line, is_silent=False):
    if not is_silent:
        print_out(line)
    s.sendall(line + '\r\n')
    return

####

def signal_handler(signal, frame):
    close(config_fp)
    if s:
        write('QUIT ' + VERSION)
        s.close()
    print_out('Exiting...')
    sys.exit(0)

#### Start

VERSION  = 'EnigmaIRCb v0.1beta'
GREETING = 'Welcome to ' + VERSION + '!'

signal.signal(signal.SIGINT, signal_handler)

config = RawConfigParser()
config_fp = open('server.cfg')
config.readfp(config_fp)

print_out('='*len(GREETING))
print_out(GREETING)
print_out('='*len(GREETING))

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((get_config('hostname'), get_config_int('port')))

if get_config_bool('use_ssl'):
    s = ssl.wrap_socket(s)

f = s.makefile()

if s is None:
    print_out('Failed to connect to host (' + get_config('hostname') + ')')
    sys.exit(1)

#### Registration
write('NICK ' + get_config('nickname'))
write('USER ' + get_config('nickname') + ' ' + get_config('nickname') + ' ' + get_config('nickname') + ' : ' + get_config('realname'))

channel_users = {}

line = f.readline().rstrip()
while line:
    message_parts = line.split(' ')
    if get_config_bool('show_motd') or len(message_parts) < 2 or message_parts[1] not in ['372','375','376']:
        print_out(line)
    if message_parts[0] == 'PING':
        write('PONG ' + message_parts[1])
    elif len(message_parts) > 4 and message_parts[3] == ':PING':
        send_notice(extract_nick(line), 'PONG ' + message_parts[4])
    elif len(line.split(':')) > 2 and line.split(':')[2] == 'VERSION':
        send_notice(extract_nick(line), 'VERSION ' + VERSION + '')
    elif len(message_parts) > 2 and message_parts[1] == 'JOIN':
        nick = extract_nick(line)
        channel = message_parts[2][1:].lower()
        if is_my_nick(nick):
            channel_users[channel] = []
        else:
            channel_users[channel].append(nick)
    elif len(message_parts) > 2 and message_parts[1] == 'PART':
        channel_users[message_parts[2]].remove(extract_nick(line))
    elif len(message_parts) > 1 and message_parts[1] == 'QUIT':
        nick = extract_nick(line)
        for channel, users in channel_users.iteritems():
            if nick in users:
                channel_users[channel].remove(nick)
#### Server Messages
    elif extract_reply_code(line):
        if reply_code == 1:
            user_identify()
            user_set_modes(get_config('usermodes'))
            for channel in get_config_list('channels'):
                user_join_channel(channel)
        elif reply_code == 353:
            channel = message_parts[4]
            for nick in line.split(':', 2)[2].split(' '):
                if nick[0] in get_config_list('oper_prefixes'):
                    channel_users[channel].append(nick[1:])
                else:
                    channel_users[channel].append(nick)
            channel_users[channel].sort()
#### User Commands
    elif extract_command(line):
        if command == 'version':
            send_privmsg(extract_target(line), 'Version: ' + VERSION)

    line = f.readline().rstrip()
else:
    print_out('Connection closed')
    s.close()
