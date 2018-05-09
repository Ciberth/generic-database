#!/usr/bin/python

import pwd
import os
from subprocess import call
from charmhelpers.core import host
from charmhelpers.core.hookenv import log, status_set, config
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_flag, clear_flag, when_file_changed, endpoint_from_flag
from charms.reactive import Endpoint

# Once this generic database becomes concrete the following dictionary will keep all information

db_details = {}

@when('apache.available')
def finishing_up_setting_up_sites():
    host.service_reload('apache2')
    set_flag('apache.start')

@when('apache.start')
def ready():
    host.service_reload('apache2')
    status_set('active', 'apache ready')

# only postgres for now, but same idea for mysql, mongo for following 2 functions


@when('pgsqldb.connected', 'endpoint.generic-database.postgresql.requested')
def request_postgresql_db():
    pgsql_endpoint = endpoint_from_flag('pgsqldb.connected')
    pgsql_endpoint.set_database('dbname_abc')
    status_set('maintenance', 'Requesting pgsql db')


@when('pgsqldb.master.available', 'endpoint.generic-database.postgresql.requested')
def render_pgsql_config_and_share_details():   
    pgsql_endpoint = endpoint_from_flag('pgsqldb.master.available')
    
    # fill dictionary 
    db_details['technology'] = "postgresql"
    db_details['password'] = pgsql_endpoint.master['password']
    db_details['dbname'] = pgsql_endpoint.master['dbname']
    db_details['host'] = pgsql_endpoint.master['host']
    db_details['user'] = pgsql_endpoint.master['user']
    db_details['port'] = pgsql_endpoint.master['port']

    # On own apache
    render('gdb-config.j2', '/var/www/generic-database/gdb-config.html', {
        'db_master': pgsql_endpoint.master,
        'db_pass': pgsql_endpoint.master['password'],
        'db_dbname': pgsql_endpoint.master['dbname'],
        'db_host': pgsql_endpoint.master['host'],
        'db_user': pgsql_endpoint.master['user'],
        'db_port': pgsql_endpoint.master['port'],
    })
    # share details to consumer-app
    gdb_endpoint = endpoint_from_flag('endpoint.generic-database.postgresql.requested')
    
    gdb_endpoint.share_details(
        "postgresql",
        pgsql_endpoint.master['host'],
        pgsql_endpoint.master['dbname'],
        pgsql_endpoint.master['user'],
        pgsql_endpoint.master['password'],
        pgsql_endpoint.master['port'],
    )
    
    clear_flag('endpoint.generic-database.postgresql.requested')
    set_flag('endpoint.generic-database.postgresql.available')
    set_flag('endpoint.generic-database.concrete')
    set_flag('restart-app')

# todo config changed ?
# todo when new charms gets a new relation to this charm - share the details of the chosen db connection
# something like @when('endpoint.generic-database.concrete')

@when('restart-app')
def restart_app():
    host.service_reload('apache2')
    clear_flag('restart-app')
    status_set('active', 'Apache/gdb ready')
