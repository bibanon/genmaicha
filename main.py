import re
import socket
import threading
import os
import binascii

irc_server = 'irc.uworld.se'
irc_port = 6667
irc_channel = '#bibanon-ab'
irc_nick = 'archivebot'
irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc.connect((irc_server, irc_port))

exception_file = 'exceptions'
irc_log_file = 'irclog'

def irc_bot_listener():
    while True:
        irc_message = irc.recv(2048)
        with open(irc_log_file, 'a') as file:
            file.write(irc_message)
        if 'PING :' in irc_message:
            message = re.search(r'^[^:]+:(.*)$', irc_message).group(1)
            irc.send('PONG :' + message + '\n')
        elif re.search(r'^:.+PRIVMSG[^:]+:!.*', irc_message):
            command = re.search(r'^:.+PRIVMSG[^:]+:(!.*)', irc_message).group(1).replace('\r', '').replace('\n', '').split(' ')
            user = re.search(r'^:([^!]+)!', irc_message).group(1)
            if command[0] in ('!a', '!archive', '!ao', '!archive-only', '!abort'):
                command_archive(command, user) 

def irc_bot_print(channel, message):
    try:
        irc.send("PRIVMSG " + channel + " :" + message + "\n")
    except Exception as exception:
        with open(exception_file, 'a') as exceptions:
            exceptions.write(str(version) + '\n' + str(exception) + '\n\n')
        irc_bot_join()
    print("IRC BOT: " + message)

def command_archive(message, user):
    if len(message) == 1:
        irc_bot_print(irc_channel, user + ': What do you want to do?')
    elif message[1].startswith('http://') or message[1].startswith('https://'):
        if message[0] in ('!a', '!archive'):
            threading.Thread(target = archive, args = (message, user, 'Site')).start()
        elif message[0] in ('!ao', '!archive-only'):
            threading.Thread(target = archive, args = (message+['--1'], user, 'Webpage')).start()
    elif message[0] == '!abort':
        if not message[1]:
            irc_bot_print(irc_channel, user + ': Please specify a job.')
        else:
            for item in os.listdir('./'):
                if item.endswith(message[1][:8]):
                    stopfile = './' + item + '/stop'
                    open(stopfile, 'w').close()
                    break
            else:
                irc_bot_print(irc_channel, user + ': No job was found running with ID ' + message[1] + '.')
    else:
        irc_bot_print(irc_channel, user + ': I can only handle http:// and https://.')     

def dashboard():
    os.system('~/.local/bin/gs-server')

def archive(message, user, kind):
    job_id = binascii.hexlify(os.urandom(20))
    concurrency = '3'
    delay = '350-750'
    optioncommands = ('--con', '--concurrency', '--delay')
    commandslist = ('--igsets', '--no-offsite-links', '--igon', '--no-video', '--no-sitemaps', '--no-dupespotter', '--concurrency', '--delay', '--1')
    for command in message[2:]:
        if '=' in command:
            if command.startswith('--concurrency') or command.startswith('--con'):
                concurrency = command.split('=')[1]
            elif command.startswith('--delay'):
                delay = command.split('=')[1]
        if not command.split('=')[0] in commandslist+optioncommands:
            irc_bot_print(irc_channel, user + ': ' + command + ' is not supported.')
            break
    else:
        irc_bot_print(irc_channel, user + ': ' + kind + ' ' + message[1] + ' is being archived with ID ' + job_id + '.')
        finish = os.system('~/.local/bin/grab-site ' + message[1] + ' --id=' + job_id + ' --concurrency=' + concurrency + ' --delay=' + delay + ' ' + ' '.join([command for command in message[2:] if command in commandslist]) + ' --warc-max-size=524288000')
        print(finish)
        if finish == 0:
            newmessage = message[1]
            irc_bot_print(irc_channel, user + ': ' + kind + ' ' + message[1] + ' with ID ' + job_id + ' is archived.')
        elif finish == 256:
            irc_bot_print(irc_channel, user + ': ' + kind + ' ' + message[1] + ' with ID ' + job_id + ' was aborted.')
        else:
            irc_bot_print(irc_channel, user + ': ' + kind + ' ' + message[1] + ' with ID ' + job_id + ' is not archived correctly.')

def main():
    irc.send('USER ' + irc_nick + ' ' + irc_nick + ' ' + irc_nick + ' :This is the bot for ' + irc_channel + '.\n')
    irc.send('NICK ' + irc_nick + '\n')
    irc.send('JOIN ' + irc_channel + '\n')
    threading.Thread(target = irc_bot_listener).start()
    threading.Thread(target = dashboard).start()

if __name__ == '__main__':
    main()
