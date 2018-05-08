#!/usr/bin/python

import pwd
import os
from subprocess import call
from charmhelpers.core import host
from charmhelpers.core.hookenv import log, status_set, config
from charmhelpers.core.templating import render
from charms.reactive import when, when_not, set_flag, clear_flag, when_file_changed

@when('apache.available')
def finishing_up_setting_up_sites():
    host.service_reload('apache2')
    set_flag('apache.start')

@when('apache.start')
def ready():
    host.service_reload('apache2')
    status_set('active', 'apache ready')
    # temp to set flag here
    set_flag('gdb.pgsql.requested')

# only postgres for now, but same idea for mysql, mongo for following 2 functions


@when('pgsqldb.connected', 'generic-database.postgresql.requested')
def request_postgresql_db(pgsql):
    pgsql.set_database('dbname_abc')
    status_set('maintenance', 'Requesting pgsql db')


@when('pgsqldb.master.available', 'generic-database.postgresql.requested')
def render_pgsql_config_and_share_details(pgsql):   
    # On own apache
    render('gdb-config.j2', '/var/www/generic-database-charm/gdb-config.html', {
        'db_master': pgsql.master,
        'db_pass': pgsql.master['password'],
        'db_dbname': pgsql.master['dbname'],
        'db_host': pgsql.master['host'],
        'db_user': pgsql.master['user'],
        'db_port': pgsql.master['port'],
    })
    # share details to consumer-app
    endpoint = endpoint_from_flag('generic-database.postgresql.requested')
    
    endpoint.share_details(
        "postgresql",
        pgsql.master['host'],
        pgsql.master['dbname'],
        pgsql.master['user'],
        pgsql.master['password'],
        pgsql.master['port'],
    )
    
    clear_flag('generic-database.postgresql.requested')
    set_flag('generic-database.postgresql.available')
    set_flag('generic-database.concrete')
    set_flag('restart-app')

# todo config changed ?
# todo when new charms gets a new relation to this charm - share the details of the chosen db connection
# something like @when('generic-database.concrete')

@when('restart-app')
def restart_app():
    host.service_reload('apache2')
    clear_flag('restart-app')
    status_set('active', 'Apache ready')
