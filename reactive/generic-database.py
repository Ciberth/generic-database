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
db_details['technology'] = "placeholder"
db_details['dbname'] = "placeholder"

################################################
#                                              #
# Apache stuff                                 #
#                                              #
################################################


@when('apache.available')
def finishing_up_setting_up_sites():
    host.service_reload('apache2')
    set_flag('apache.start')

@when('apache.start')
def ready():
    host.service_reload('apache2')
    status_set('active', 'apache ready - gdb not concrete')

# only postgres for now, but same idea for mysql, mongo for following 2 functions

###############################################
#
# Postgresql support
#
###############################################


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


###############################################
#
# Mysql support
#
###############################################

@when('mysqldb.connected', 'endpoint.generic-database.mysql.requested')
def request_mysql_db():
    mysql_endpoint = endpoint_from_flag('mysqldb.connected')
    mysql_endpoint.configure('gdb_mysql_db', 'gdb_mysql_user', prefix="gdb")
    # todo
    # username = unit-name-user ; password = generated ; dbname = unit-name-db ; prefix = gdb (only 1 db anyways)
    status_set('maintenance', 'Requesting mysql db')


@when('mysqldb.available', 'endpoint.generic-database.mysql.requested')
def render_mysql_config_and_share_details():   
    mysql_endpoint = endpoint_from_flag('mysqldb.available')
    
    # fill dictionary 
    db_details['technology'] = "mysql"
    db_details['password'] = mysql_endpoint.password("gdb")
    db_details['dbname'] = mysql_endpoint.database("gdb")
    db_details['host'] = mysql_endpoint.db_host()
    db_details['user'] = mysql_endpoint.username("gdb")
    db_details['port'] = "3306"

    # On own apache
    render('gdb-config.j2', '/var/www/generic-database/gdb-config.html', {
        'db_master': "no-master",
        'db_pass': mysql_endpoint.password("gdb"),
        'db_dbname': mysql_endpoint.database("gdb"),
        'db_host': mysql_endpoint.db_host(),
        'db_user': mysql_endpoint.username("gdb"),
        'db_port': "3306",
    })
    # share details to consumer-app
    gdb_endpoint = endpoint_from_flag('endpoint.generic-database.mysql.requested')
    
    gdb_endpoint.share_details(
        "mysql",
        mysql_endpoint.db_host(),
        mysql_endpoint.database("gdb"),
        mysql_endpoint.username("gdb"),
        mysql_endpoint.password("gdb"),
        "3306",
    )
    
    clear_flag('endpoint.generic-database.mysql.requested')
    set_flag('endpoint.generic-database.mysql.available')
    set_flag('endpoint.generic-database.concrete')
    set_flag('restart-app')



@when('restart-app')
def restart_app():
    host.service_reload('apache2')
    clear_flag('restart-app')
    status_set('active', 'Apache/gdb ready and concrete')


# A new relation is added to an already concrete generic database
if db_details['dbname']:
    request_flag = 'endpoint.generic-database.' + db_details['dbname'] + '.requested'

@when('endpoint.generic-database.concrete', request_flag)
def share_details_to_new_relation():
    gdb_endpoint = endpoint_from_flag(request_flag)
    
    if gdb_endpoint['dbname'] == db_details['dbname']:

        gdb_endpoint.share_details(
            db_details['technology'],
            db_details['host'],
            db_details['dbname'],
            db_details['user'],
            db_details['password'],
            db_details['port'],
        )
    dbname_flag = 'endpoint.generic-database.' + db_details['dbname'] + '.requested'
    clear_flag(dbname_flag)
