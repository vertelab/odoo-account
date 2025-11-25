#!/usr/bin/env python3
import argparse
import base64
import logging
import multiprocessing
import os
import re
import signal
from configparser import ConfigParser
import inotify.adapters
from odoorpc import ODOO
from odoorpc.error import RPCError


# Loggningskonfiguration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/odoo/account_move_directory.log'),
        logging.StreamHandler()
    ]
)

def read_admin_password():
    config = ConfigParser()
    config.read('/etc/odoo/odoo.conf')
    return config.get('options', 'admin_passwd')

def get_all_databases():
    """TODO: to be used later"""
    try:
        odoo = ODOO('localhost', port=8069)
        databases = odoo.db.list()
        return databases
    except Exception as e:
        logging.error(f'Failed to get databases from Odoo: {e}')
        return []

def connect_to_odoo(database):
    admin_password = read_admin_password()
    try:
        odoo = ODOO('localhost', port=8069)
        odoo.login(database, 'admin', admin_password)
        return odoo
    except RPCError as e:
        logging.error(f'Fel vid anslutning till Odoo-databas {database}: {e}')
        return None

def get_move_directory(odoo):
    param = odoo.env['ir.config_parameter'].search_read(
        [('key', '=', 'account_move_directory')], ['key', 'value'], limit=1
    )
    if param:
        logging.info(f"Account Attachment Directory: {param[0].get('value')}")
        return param[0].get('value')
    else:
        return None

def process_file(file_path, odoo):
    file_name = os.path.basename(file_path)
    match = re.match(r'(.*)_(.*)\.(.*)', file_name)
    if match:
        verifikat_id = match.group(1)
        file_extension = match.group(3)
        # Använd wildcard för sökningen om filnamnet innehåller "-"
        verifikat_id = verifikat_id.replace('-', '%')
        if verifikat_id:
            try:
                with open(file_path, 'rb') as f:
                    odoo.env['edi.message'].browse(odoo.env['edi.message'].create({
                        'name': os.path.splitext(file_name)[0],
                        'payload': base64.b64encode(f.read()).decode('utf-8'),
                    })).unpack()

                logging.info(f'The file {file_name} has been added as an attachment')
                # Radera filen
                os.remove(file_path)
            except Exception as e:
                logging.error(f'Fel vid bearbetning av fil {file_name}: {e}')
                # Flytta filen till underkatalogen error-files
                error_dir = os.path.join(os.path.dirname(file_path), 'error-files')
                if not os.path.exists(error_dir):
                    os.makedirs(error_dir)
                os.rename(file_path, os.path.join(error_dir, file_name))
        else:
            logging.error(f'Verifikatet {verifikat_id} hittades inte')
    else:
        logging.error(f'Felaktigt filnamn {file_name}')



def watch_directory(database, move_directory):
    odoo = connect_to_odoo(database)
    if odoo:
        # Watch the directory
        i = inotify.adapters.Inotify()
        i.add_watch(move_directory, mask=inotify.constants.IN_CLOSE_WRITE)
        logging.info(f'Watching directory: {move_directory}')
        for event in i.event_gen():
            if event:
                file_path = os.path.join(move_directory, event[3])
                process_file(file_path, odoo)


def main():
    parser = argparse.ArgumentParser(description='Odoo Database Watcher')
    parser.add_argument('-d', '--db', required=True, help='Comma separated list od Odoo Databases')
    args = parser.parse_args()

    processes = []
    for database in  [name.strip() for name in args.db.split(',')]:
        odoo = connect_to_odoo(database)
        if odoo:
            move_directory = get_move_directory(odoo)
            if move_directory:
                p = multiprocessing.Process(
                    target=watch_directory, args=(database, move_directory)
                )
                p.start()
                processes.append(p)

    try:
        while True:
            pass
    except KeyboardInterrupt:
        # Avsluta alla processer
        for p in processes:
            os.kill(p.pid, signal.SIGTERM)
        # Vänta på att alla processer ska avslutas
        for p in processes:
            p.join()

 
if __name__ == '__main__':
    main()
