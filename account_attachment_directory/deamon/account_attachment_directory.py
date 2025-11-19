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
        logging.FileHandler('/var/log/odoo/account_attachment_directory.log'),
        logging.StreamHandler()
    ]
)

def read_admin_password():
    config = ConfigParser()
    config.read('/etc/odoo.conf')
    return config.get('options', 'admin_passwd')

def connect_to_odoo(database):
    admin_password = read_admin_password()
    try:
        odoo = ODOO('http://localhost', port=8069)
        odoo.login(database, 'admin', admin_password)
        return odoo
    except RPCError as e:
        logging.error(f'Fel vid anslutning till Odoo-databas {database}: {e}')
        return None

def get_attachment_directory(odoo):
    param = odoo.env['ir.config_parameter'].search_read(
        [('key', '=', 'account_attachment_directory')], ['key', 'value'], limit=1
    )
    if param:
        logging.info(f"Account Attachment Directory: {param[0].get('value')}")
        return param[0].get('value')
    else:
        return None

def process_file(file_path, odoo):
    file_name = os.path.basename(file_path)
    match = re.match(r'(.*)_(.*)\.(.*)', file_name)
    AccountMove = odoo.env['account.move']
    if match:
        verifikat_id = match.group(1)
        file_extension = match.group(3)
        # Använd wildcard för sökningen om filnamnet innehåller "-"
        verifikat_id = verifikat_id.replace('-', '%')
        verifikat = AccountMove.search([
            ('name', 'like', verifikat_id), ('move_type', 'not in', ['in_refund', 'out_refund'])
        ], limit=1)
        if verifikat:
            try:
                with open(file_path, 'rb') as f:
                    odoo.env['ir.attachment'].create({
                        'name': os.path.splitext(file_name)[0],
                        'datas': base64.b64encode(f.read()).decode('utf-8'),
                        'res_model': 'account.move',
                        'res_id': verifikat[0]
                    })
                logging.info(f'Filen {file_name} har lagts till som bilaga på verifikatet {verifikat_id}')
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


def watch_directory(database, attachment_directory):
    odoo = connect_to_odoo(database)
    if odoo:
        # Watch the directory
        i = inotify.adapters.Inotify()
        i.add_watch(attachment_directory, mask=inotify.constants.IN_CLOSE_WRITE)
        logging.info(f'Watching directory: {attachment_directory}')
        for event in i.event_gen():
            if event:
                file_path = os.path.join(attachment_directory, event[3])
                process_file(file_path, odoo)


def main():
    parser = argparse.ArgumentParser(description='Odoo Database Watcher')
    parser.add_argument('-d', '--db', required=True, help='Comma separated list od Odoo Databases')
    args = parser.parse_args()

    processes = []
    for database in  [name.strip() for name in args.db.split(',')]:
        odoo = connect_to_odoo(database)
        if odoo:
            attachment_directory = get_attachment_directory(odoo)
            if attachment_directory:
                p = multiprocessing.Process(
                    target=watch_directory, args=(database, attachment_directory)
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
