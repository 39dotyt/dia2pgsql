#!/usr/bin/python2
# -*- coding: utf-8 -*-
__author__ = 'Yurij Mikhalevich <count@ypsilon.me>'
__version__ = '0.1'

import sys
from lxml import etree

nsmap = {'dia': 'http://www.lysator.liu.se/~alla/dia/'}
sequence_pre = ''
sequence_post = ''
enums = ''
tables = ''
triggers = ''
insert = ''
fks = ''
tables_to_be_triggered_with_ut = []
tables_to_be_triggered_with_st = []


def class2table(element):
    if element.find('dia:attribute[@name="fill_color"]/dia:color', namespaces=nsmap).get('val') != '#e6e6e6':
        table_name = element.findtext('dia:attribute[@name="name"]/dia:string', namespaces=nsmap)[1:-1]
        query = 'CREATE TABLE %s (\n' % table_name
        for attr in element.iterfind('.//dia:composite[@type="umlattribute"]', namespaces=nsmap):
            attr_name = attr.findtext('dia:attribute[@name="name"]/dia:string', namespaces=nsmap)[1:-1]
            if attr_name == 'time_of_last_change':
                global tables_to_be_triggered_with_ut
                tables_to_be_triggered_with_ut.append(table_name)
            elif attr_name == 'timestamp':
                global tables_to_be_triggered_with_st
                tables_to_be_triggered_with_st.append(table_name)
            attr_type = attr.findtext('dia:attribute[@name="type"]/dia:string', namespaces=nsmap)[1:-1]
            attr_value = attr.findtext('dia:attribute[@name="value"]/dia:string', namespaces=nsmap)[1:-1]
            attr_visibility = attr.find('dia:attribute[@name="visibility"]/dia:enum',
                                        namespaces=nsmap).get('val')
            if attr_visibility != '1':
                query += '    %s %s' % (attr_name, attr_type)
                if attr_value:
                    query += ' %s' % attr_value
                if attr_visibility == '2':
                    query += ' PRIMARY KEY'
                query += ',\n'
        query = query[:-2] + '\n) WITH (\n    oids=false\n);'
        global tables
        tables += query + '\n'


def parse_smallpackage(element):
    type = element.findtext('dia:attribute[@name="stereotype"]/dia:string', namespaces=nsmap)[1:-1]
    content = element.findtext('.//dia:attribute[@name="string"]/dia:string', namespaces=nsmap)[1:-1]
    if type.startswith('enum'):
        query = 'CREATE TYPE %s AS ENUM (' % type[5:]
        content = content.split('\n')
        for entry in content:
            query += '\'%s\', ' % entry
        query = query[:-2] + ');'
        global enums
        enums += query + '\n'
    elif type == 'pre':
        global sequence_pre
        sequence_pre += content + '\n'
    elif type == 'post':
        global sequence_post
        sequence_post += content + '\n'


def component2insert(element):
    name = element.findtext('dia:attribute[@name="stereotype"]/dia:string', namespaces=nsmap)[1:-1]
    [table_name, inserted_fields] = name.split(':')
    query = 'INSERT INTO %s (%s) VALUES\n' % (table_name, inserted_fields)
    content = element.findtext('.//dia:attribute[@name="string"]/dia:string',
                               namespaces=nsmap)[1:-1].split('\n')
    for values in content:
        query += '    (%s),\n' % values
    global insert
    insert += query[:-2] + ';\n'


def association2foreignkey(element):
    field_from = element.findtext('dia:attribute[@name="role_a"]/dia:string', namespaces=nsmap)[1:-1]
    field_to = element.findtext('dia:attribute[@name="role_b"]/dia:string', namespaces=nsmap)[1:-1]
    tables = element.find('dia:connections', namespaces=nsmap)
    table_from = diagram.findtext('.//dia:object[@id="%s"]/dia:attribute[@name="name"]/dia:string'
                                  % tables.find('dia:connection[@handle="0"]', namespaces=nsmap).get('to'),
                                  namespaces=nsmap)[1:-1]
    table_to = diagram.findtext('.//dia:object[@id="%s"]/dia:attribute[@name="name"]/dia:string'
                                % tables.find('dia:connection[@handle="1"]', namespaces=nsmap).get('to'),
                                namespaces=nsmap)[1:-1]
    global fks
    fks += ('alter table %s add constraint %s_%s2%s_%s foreign key (%s) references %s (%s) match full;\n'
            % (table_from, table_from, field_from, table_to, field_to, field_from, table_to, field_to))


def create_triggers():
    global triggers
    for table in tables_to_be_triggered_with_ut:
        triggers += ('create trigger c_tmpstmp_%s\n'
                     '    before insert\n'
                     '    on %s\n'
                     '    for each row\n'
                     '    execute procedure upd_timestamp();\n'
                     % (table, table))
        triggers += ('create trigger u_tmpstmp_%s\n'
                     '    before update\n'
                     '    on %s\n'
                     '    for each row\n'
                     '    execute procedure upd_timestamp();\n'
                     % (table, table))
    for table in tables_to_be_triggered_with_st:
        triggers += ('create trigger s_tmpstmp_%s\n'
                     '    before insert\n'
                     '    on %s\n'
                     '    for each row\n'
                     '    execute procedure set_timestamp();\n'
                     % (table, table))

if __name__ == '__main__':
    global diagram
    diagram = etree.parse(sys.argv[1:][0])
    for element in diagram.iterfind('.//dia:object[@type="UML - SmallPackage"]', namespaces=nsmap):
        parse_smallpackage(element)
    for element in diagram.iterfind('.//dia:object[@type="UML - Class"]', namespaces=nsmap):
        class2table(element)
    for element in diagram.iterfind('.//dia:object[@type="UML - Component"]', namespaces=nsmap):
        component2insert(element)
    for element in diagram.iterfind('.//dia:object[@type="UML - Association"]', namespaces=nsmap):
        association2foreignkey(element)
    create_triggers()
    print sequence_pre.encode('utf8')
    print enums.encode('utf8')
    print tables.encode('utf8')
    print sequence_post.encode('utf8')
    print triggers.encode('utf8')
    print insert.encode('utf8')
    print fks.encode('utf8')
