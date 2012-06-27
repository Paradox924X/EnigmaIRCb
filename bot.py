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

config = RawConfigParser()
user_config = RawConfigParser()
command_config = RawConfigParser()

####

def get_config(key, cfg=config):
    return cfg.get('enigma-irc-bot', key)

def get_config_bool(key, cfg=config):
    return cfg.getboolean('enigma-irc-bot', key)

def get_config_int(key, cfg=config):
    return cfg.getint('enigma-irc-bot', key)

def get_config_float(key, cfg=config):
    return cfg.getfloat('enigma-irc-bot', key)

def get_config_list(key, cfg=config):
    temp_list = get_config(key, cfg).split(',')
    for index, entry in enumerate(temp_list):
        temp_list[index] = entry.strip()
    return temp_list

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
        if command not in commands:
            command = None
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

def user_request_auth(user):
    if user not in authed_users:
        send_privmsg(get_config('nickserv'), 'STATUS ' + user)
        return True
    return False

def user_auth(user):
    if user not in authed_users:
        authed_users.append(user)
        authed_users.sort()
    return

def user_deauth(user):
    if user not in authed_users:
        return False
    authed_users.remove(user)
    return True

def user_check_auth(user, command):
    if command not in commands:
        return False
    authed_groups = command_groups_list[commands.index(command)]
    if '*' in authed_groups:
        return True
    if user not in users or user not in authed_users:
        return False
    for authed_group_index, authed_group in enumerate(authed_groups):
        authed_group_users = group_users_list[groups.index(authed_group)]
        if user in authed_group_users:
            return True
    return False

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
    command_config_fp.close()
    user_config_fp.close()
    config_fp.close()
    if s:
        write('QUIT ' + VERSION)
        s.close()
    print_out('Exiting...')
    sys.exit(0)

#### Start

VERSION          = 'EnigmaIRCb v0.2beta'
GREETING         = 'Welcome to ' + VERSION + '!'
CONFIG_FILE_NAME = 'bot.cfg'

signal.signal(signal.SIGINT, signal_handler)

config_fp = open(CONFIG_FILE_NAME)
config.readfp(config_fp)

user_config_fp = open(get_config('user_config'))
user_config.readfp(user_config_fp)

command_config_fp = open(get_config('command_config'))
command_config.readfp(command_config_fp)

users = []
authed_users = []

groups, group_users_list = map(list, zip(*user_config.items('enigma-irc-bot')))
for group_users_index, group_users in enumerate(group_users_list):
    group_users = group_users.split(',')
    for group_user_index, group_user in enumerate(group_users):
        group_user = group_user.strip()
        group_users[group_user_index] = group_user
        if group_user not in users:
            users.append(group_user)
    group_users_list[group_users_index] = group_users
users.sort()

commands, command_groups_list = map(list, zip(*command_config.items('enigma-irc-bot')))
for command_groups_index, command_groups in enumerate(command_groups_list):
    command_groups = command_groups.split(',')
    for command_group_index, command_group in enumerate(command_groups):
        command_group = command_group.strip()
        command_groups[command_group_index] = command_group
        if command_group not in groups and command_group is not '*':
            print_out("FATAL ERROR: Unrecognized group '" + command_group + "' specified for command '" + commands[command_groups_list.index(command_groups)] + "'")
            command_config.close()
            user_config.close()
            config.close()
            sys.exit(1)
    command_groups_list[command_groups_index] = command_groups

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
        if nick in authed_users:
            authed_users.remove(nick)
#### NickServ Messages
    elif extract_nick(line) == get_config('nickserv'):
        if message_parts[1] == 'NOTICE' and message_parts[3][1:] == 'STATUS':
            nick = message_parts[4]
            if message_parts[5] == '3':
                user_auth(nick)
                send_notice(nick, 'You have been successfully authenticated.')
            else:
                send_notice(nick, 'Failed to authenticate with ' + get_config('nickserv') + '.')
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
    elif extract_command(line) and user_check_auth(extract_nick(line), command):
        if command == 'auth':
            if not user_request_auth(extract_nick(line)):
                send_notice(nick, 'You are already authenticated.')
        elif command == 'commands':
            commands_sorted = commands
            commands_sorted.sort()
            send_privmsg(extract_target(line), 'Commands: ' + ', '.join(commands_sorted))
        elif command == 'deauth':
            nick = extract_nick(line)
            if user_deauth(nick):
                send_notice(nick, 'You have been successfully deauthenticated.')
            else:
                send_notice(nick, 'You are not authenticated.')
        elif command == 'version':
            send_privmsg(extract_target(line), 'Version: ' + VERSION)

    line = f.readline().rstrip()
else:
    print_out('Connection closed')
    s.close()
