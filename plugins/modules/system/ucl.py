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
# * Implement? tests/get_07.cmd 'get --shellvars --keys --expand .|recurse'
#
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 


from __future__ import absolute_import, division, print_function
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
    returned: success
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
    sample:
stderr:
message:
diff: []
'''

import os

from ansible.module_utils.basic import AnsibleModule, json_dict_bytes_to_unicode
from ansible.module_utils._text import to_bytes

def get_value(module, uclcmd_path, options, path, upath):
    """ Get value of upath """

    changed = False
    msg = ''
    cmd = "%s get %s -f %s %s" % (uclcmd_path, options, path, upath)
    rc, out, err = module.run_command(cmd)
    return (changed, cmd, rc, out, err, msg)


def set_value(module, uclcmd_path, options, path, upath, merge, value, ipath):
    """ Set value of upath. Optionally use content of ipath. Optionally merge. """

    changed = False
    msg = ''
    if merge:
        if value:
            cmd = "%s merge %s -f %s %s %s" % (uclcmd_path, options, path, upath, value)
        elif ipath:
            cmd = "%s merge %s -f %s -i %s %s" % (uclcmd_path, options, path, ipath, upath)
    else:
        if value:
            cmd = "%s set %s -f %s %s %s" % (uclcmd_path, options, path, upath, value)
        elif ipath:
            cmd = "%s set %s -f %s -i %s %s" % (uclcmd_path, options, path, ipath, upath)

    rc, out, err = module.run_command(cmd)
    return (changed, cmd, rc, out, err, msg)


def remove_upath(module, uclcmd_path, options, path, upath):
    """ Remove upath """

    changed = False
    msg = ''
    b_dest = to_bytes(path, errors='surrogate_or_strict')
    if not os.path.exists(b_dest):
        module.exit_json(changed=False, msg="file not present")

    diff = {'before': '',
            'after': '',
            'before_header': '%s (content)' % path,
            'after_header': '%s (content)' % path}
    # There is no stdout from the *uclcmd* command wihtout --noop if
    # *set* or *merge*
    # TODO: diff shall be available for *ansible-playbook --diff*
    if module.check_mode and module._diff:
        with open(b_dest, 'rb') as f:
            diff['before'] = f.read()
        
    cmd = "%s remove %s -f %s %s" % (uclcmd_path, options, path, upath)
    rc, out, err = module.run_command(cmd)

    if module.check_mode and module._diff:
        diff['after'] = out
    attr_diff = {}
    attr_diff['before_header'] = '%s (file attributes)' % path
    attr_diff['after_header'] = '%s (file attributes)' % path
    difflist = [diff, attr_diff]
    msg, changed = check_file_attrs(module, changed, msg, attr_diff)

    return (changed, cmd, rc, out, err, msg, difflist)


def check_file_attrs(module, changed, message, diff):
    
    file_args = module.load_file_common_arguments(module.params)
    if module.set_fs_attributes_if_different(file_args, False, diff=diff):
        if changed:
            message += " and "
        changed = True
        message += "ownership, perms or SE linux context changed"

    return (message, changed)
    

def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='path', aliases=['dest', 'file']),
            upath=dict(type='str', aliases=['variable', 'key']),
            ipath=dict(type='str'),
            value=dict(type='raw'),
            merge=dict(type='bool', default=False),
            state=dict(type='str', default='present', choices=['absent', 'present'], aliases=['ensure']),
            delimiter=dict(type='str', default='.'),
            format=dict(type='str', default='ucl'),
        ),
        supports_check_mode=True,
        mutually_exclusive=[
            ['path', 'uclstring'],
            ['value', 'ipath'],
        ],
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
    if module.check_mode or module._diff:
        options += " --noop"

    r = {'changed': False, 'cmd': '', 'rc': None, 'stdout': '', 'stderr': '', 'message': '', 'diff': []}

    # Set value if either *value* or *ipath* is defined
    if state == 'present' and (value or ipath):
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'] = \
        set_value(module, uclcmd_path, options, path, upath, merge, value, ipath)

    # Get value if neither *value* nor *ipath* is defined
    elif state == 'present':
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'] = \
        get_value(module, uclcmd_path, options, path, upath)

    # Remove *upath*
    elif state == 'absent':
        r['changed'], r['cmd'], r['rc'], r['stdout'], r['stderr'], r['message'], r['diff'] = \
        remove_upath(module, uclcmd_path, options, path, upath)

    module.exit_json(**r)


if __name__ == '__main__':
    main()
