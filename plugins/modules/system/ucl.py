#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2021, Vladimir Botka <vbotka@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# TODO - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# * Sanity
#   - required: uclcmd
#   - exists: path, ipath
#
# * Options
#   --type ..... make the new element this type
#   --noquotes   do not enclose strings in quotes
#   --nonewline  separate output with spaces rather than newlines
#   --keys       show key=value rather than just the value
#   --expand     Output the list of keys when encountering an object
#   UCL ........ A block of UCL to be written to the specified variable
#
# * Parameters
#   - owner, group, mode
#   - backup
#   - validate
#   - create path optionally?
#
#
# NOTES - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# * uclcmd's option of using stdin to input data not used. This might
#   be a functionality of a filter or a lookup plugin.
#
#   uclstring:
#     description:
#       - A string containing UCL on which to operate.
#       - This parameter is required, unless C(path) is given.
#     type: str
#
#
# BUGS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# * No diff output from *ansible-playbook --check --diff*
#
#
# QUESTIONS - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
# * Lint? UCL
# * Are uclcmd options *--input* and *UCL* mutually exclusive?
# * Implement? tests/get_07.cmd 'get --shellvars --keys --expand .|recurse'
# * Use-cases? How is uclcmd used? Best practice?
# * Ansible filter? ucl_query? Similar to json_query.
# * Ansible filter? from_ucl? Similar to from_yaml.
#
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: ucl

short_description: Manage FreeBSD UCL config files

version added: devel

description:
  - A CRUD-like interface to managing UCL files.

options:
    path:
        description:
            - Path to the file to operate on.
            - This file must exist ahead of time.
            - This parameter is required.
        type: path
        aliases: [ dest, file ]
    upath:
        description:
            - The key of the variable in object notation.
        type: str
        aliases: [ variable, key ]
    ipath:
        description:
           - File as additional input for combining or merging.
        type: path
    value:
        description:
            - Desired value of the selected variable.
            - Either a string, or to unset a value, the Python C(None) keyword (YAML Equivalent, C(null)).
        type: raw
    merge:
        description:
            - Whether the value should be merged.
        type: bool
        default: no
    state:
        description:
            - Desired state of the selected variable. Whether the variable should be there or not.
        type: str
        choices: [ absent, present ]
        default: present
        aliases: [ ensure ]
    delimiter:
        description:
            - Character to use as element delimiter.
        type: str
        default: .
    format:
        description:
            - Output format
        type: str
        choices: [ ucl, yaml, json, cjson, msgpack, shellvars ]
        default: ucl
requirements:
    - uclcmd >= 0.1_3
    - libucl >= 0.8.1
notes:
    - Supports C(check_mode).
seealso:
    - name: FreeBSD Universal Configuration Language
      description: Wiki
      link: https://wiki.freebsd.org/UniversalConfigurationLanguage
    - name: Source code devel/uclcmd
      description: Command line tool for working with UCL config files.
      link: https://github.com/allanjude/uclcmd
    - name: Source code libucl
      description: UCL library
      link: https://github.com/vstakhov/libucl/
author: "Vladimir Botka (@vbotka)"
'''

EXAMPLES = r'''
- name: Get value of variable in UCL format
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key

- name: Get value of variable in YAML format
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key
    format: yaml

- name: Set new value to variable in UCL format
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key
    value: newvalue

- name: Merge new value to variable (combine item with list) in UCL format
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key
    value: newvalue
    merge: yes

- name: Merge new value to variable (merge UCL file) in UCL format
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key
    ipath: merge.ucl
    merge: yes

- name: Remove variable
  community.general.ucl:
    path: /foo/bar.conf
    upath: rootkey.subkey.key
    state: absent
'''

RETURN = r'''
cmd:
    description: uclcmd command
    returned: always
    type: str
    sample: /usr/local/bin/uclcmd remove --ucl --delimiter . --noop -f /tests/set.in rootkey.subkey.child
rc:
    description: Return code of the command
    returned: success
    type: int
    sample: 0
stdout:
    description: Standard output from the command
    returned: success
    type: str
    sample: TODO
stderr:
    description: Standard error from the command
    returned: failure
    type: str
    sample: TODO
message:
    description: Messge
    returned: optional
    type: str
    sample: TODO
diff:
    description: Changes
    returned: When changed
    type: list
    sample: TODO
'''

import difflib

from ansible.module_utils.basic import AnsibleModule, json_dict_bytes_to_unicode

def get_value(module, uclcmd_path, options, path, upath):
    """ Get value of upath """

    changed = False
    msg = ''
    cmd = "%s get %s -f %s %s" % (uclcmd_path, options['run'], path, upath)
    rc, out, err = module.run_command(cmd)
    return (changed, cmd, rc, out, err, msg)


def set_value(module, uclcmd_path, options, path, upath, merge, value, ipath):
    """ Set value of upath. Optionally use content of ipath. Optionally merge. """

    changed = False
    msg = ''
    diff = dict(before='', after='')

    if merge:
        if value:
            cmd = "%s merge %s -f %s %s %s" % (uclcmd_path, options['run'], path, upath, value)
        elif ipath:
            cmd = "%s merge %s -f %s -i %s %s" % (uclcmd_path, options['run'], path, ipath, upath)
    else:
        if value:
            cmd = "%s set %s -f %s %s %s" % (uclcmd_path, options['run'], path, upath, value)
        elif ipath:
            cmd = "%s set %s -f %s -i %s %s" % (uclcmd_path, options['run'], path, ipath, upath)

    rc, out, err = module.run_command(cmd)
    return (changed, cmd, rc, out, err, msg, diff)


def remove_upath(module, uclcmd_path, options, path, upath):
    """ Remove upath """

    changed = False
    msg = ''

    # Record changes
    diff = dict(before='', after='', ndiff='')
    cmd = "%s get -u -f %s %s" % (uclcmd_path, path, ".")
    rc, out, err = module.run_command(cmd)
    diff['before'] = out.splitlines()
    cmd = "%s remove -n -u -f %s %s" % (uclcmd_path, path, upath)
    rc, out, err = module.run_command(cmd)
    diff['after'] = out.splitlines()
    difference = difflib.ndiff(diff['before'], diff['after'])
    diff['ndiff'] = ('\n'.join(difference)).splitlines()
    changed = len(diff['before']) != len(diff['after'])

    # Remove upath from path
    if not module.check_mode:
        cmd = "%s remove %s -f %s -o %s %s" % (uclcmd_path, options, path, path, upath)
        rc, out, err = module.run_command(cmd)

    return (changed, cmd, rc, out, err, msg, diff)


def run_module():
    module_args = dict(
        path=dict(type='path', aliases=['dest', 'file']),
        upath=dict(type='str', aliases=['variable', 'key']),
        ipath=dict(type='str'),
        value=dict(type='raw'),
        merge=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['absent', 'present'], aliases=['ensure']),
        delimiter=dict(type='str', default='.'),
        format=dict(type='str', default='ucl'),
        )

    r = dict(changed=False, cmd='', rc=None, stdout='', stderr='', message='', diff=dict())

    module = AnsibleModule(
        argument_spec=module_args,
        add_file_common_args=True,
        supports_check_mode=True,
        mutually_exclusive=[['value', 'ipath'],]
        )

    uclcmd_path = module.get_bin_path('uclcmd', True)

    p = module.params
    path = p['path']
    upath = p['upath']
    ipath = p['ipath']
    value = json_dict_bytes_to_unicode(p['value'])
    merge = p['merge']
    state = p['state']
    delimiter = p['delimiter']
    format = p['format']

    options = '--%s --delimiter %s' % (format, delimiter)

    # Set value if either *value* or *ipath* is defined
    if state == 'present' and (value or ipath):
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'] = \
        set_value(module, uclcmd_path, options, path, upath, merge, value, ipath)

    # Get value if neither *value* nor *ipath* is defined
    elif state == 'present':
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'], r['diff'] = \
        get_value(module, uclcmd_path, options, path, upath)

    # Remove *upath*
    elif state == 'absent':
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'], r['diff'] = \
        remove_upath(module, uclcmd_path, options, path, upath)

    module.exit_json(**r)


def main():
    run_module()


if __name__ == '__main__':
    main()
