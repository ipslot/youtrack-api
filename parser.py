# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import xml.etree.ElementTree

TYPE_FIELD_NAME = '{http://www.w3.org/2001/XMLSchema-instance}type'


def extract_field(name, xml_field, task):
    if xml_field.get('name') == name:
        result = xml_field.findall('value')
        if xml_field.get(TYPE_FIELD_NAME) == 'SingleField' or \
                        xml_field.get(TYPE_FIELD_NAME) == 'CustomFieldValue':
            if len(result) > 1:
                task[name] = [item.text for item in result]
            else:
                task[name] = xml_field.findall('value')[0].text
            return True
        elif xml_field.get(TYPE_FIELD_NAME) == 'LinkField':
            task[name] = [
                {
                    "value": item.text,
                    "type": item.get('type'),
                    "role": item.get('role')
                }
                for item in result
            ]
    return False


def extract_task(xml_task):
    result = {"id": xml_task.get('id'), "tags": []}
    # extract tags
    for tag in xml_task.findall('tag'):
        result['tags'].append(tag.text)
    # extract fields
    for field in xml_task.findall('field'):
        if extract_field("summary", field, result):
            continue
        if extract_field("projectShortName", field, result):
            continue
        if extract_field("numberInProject", field, result):
            continue
        if extract_field("description", field, result):
            continue
        if extract_field("created", field, result):
            continue
        if extract_field("updated", field, result):
            continue
        if extract_field("links", field, result):
            continue
        if extract_field("State", field, result):
            continue
        if extract_field("Priority", field, result):
            continue
        if extract_field("Type", field, result):
            continue
        if extract_field("Assignee", field, result):
            continue
        if extract_field("Spent time", field, result):
            continue
        if extract_field("Estimation", field, result):
            continue
    return result


def extract_task_list(string_xml_list):
    root = xml.etree.ElementTree.fromstring(string_xml_list)
    if not len(root):
        return []
    return [extract_task(child) for child in root.findall('issue')]


def extract_spent_time(xml_time_entry):
    w_type = xml_time_entry.find('worktype')
    desc = xml_time_entry.find('description')
    return {
        "id": xml_time_entry.find('id').text,
        "date": xml_time_entry.find('date').text,
        "duration": xml_time_entry.find('duration').text,
        "description": desc.text if desc is not None else None,
        "user": xml_time_entry.find('author').get("login"),
        "workType": w_type.find('name').text if w_type is not None else None
    }


def extract_spent_time_list(string_xml_list):
    root = xml.etree.ElementTree.fromstring(string_xml_list)
    if not len(root):
        return []
    return [extract_spent_time(child) for child in root.findall('workItem')]


def extract_user(xml_user_entry):
    if isinstance(xml_user_entry, str) or isinstance(xml_user_entry, bytes):
        xml_user_entry = xml.etree.ElementTree.fromstring(xml_user_entry)
    return {
        "login": xml_user_entry.get('login'),
        "name": xml_user_entry.get('fullName'),
        "url": xml_user_entry.get('url'),
    }


def extract_users(string_xml_list):
    root = xml.etree.ElementTree.fromstring(string_xml_list)
    if not len(root):
        return []
    return [extract_user(child) for child in root.findall('user')]
