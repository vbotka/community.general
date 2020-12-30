# -*- coding: utf-8 -*-
# Copyright (c) 2020, Vladimir Botka <vbotka@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible.errors import AnsibleError, AnsibleFilterError
from ansible.module_utils.six import string_types
from ansible.module_utils.common._collections_compat import Mapping, Sequence
from collections import defaultdict
from operator import itemgetter


def lists_mergeby(l1, l2, index):
    ''' merge lists by attribute index. Example:
        - debug: msg="{{ l1|community.general.lists_mergeby(l2, 'index')|list }}" '''

    if not isinstance(l1, Sequence):
        raise AnsibleFilterError('First argument for community.general.lists_mergeby must be list. %s is %s' %
                                 (l1, type(l1)))

    if not isinstance(l2, Sequence):
        raise AnsibleFilterError('Second argument for community.general.lists_mergeby must be list. %s is %s' %
                                 (l2, type(l2)))

    if not isinstance(index, string_types):
        raise AnsibleFilterError('Third argument for community.general.lists_mergeby must be string. %s is %s' %
                                 (index, type(index)))

    d = defaultdict(dict)
    for l in (l1, l2):
        for elem in l:
            if not isinstance(elem, Mapping):
                raise AnsibleFilterError('Elements of list arguments for lists_mergeby must be dictionaries. Found {0!r}.'.format(elem))
            if index in elem.keys():
                d[elem[index]].update(elem)
    return sorted(d.values(), key=itemgetter(index))


def any2items(x, key='key', override=False):
    ''' Convert any input to list.

    Example 1:

    - name: No changes to a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits: [apple, banana, orange]

       gives:

       msg:
         - apple
         - banana
         - orang

    Example 2:

    - name: Convert string to first item in a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits: 'apple'

       gives:

       msg:
         - apple

    Example 3:

    - name: Convert None to first item in a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits: None

       gives:

       msg:
         - None

    Example 4:

    - name: Convert dictionary where all values are dictionaries to a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits:
          apple:
            color: green
            size: big
          banana:
            color: yellow
            size: small

       gives:

       msg:
         - color: green
           key: apple
           size: big
         - color: yellow
           key: banana
           size: small

    Example 5:

    - name: Same as the above but change key name
      debug:
        msg: "{{ fruits|any2items(key='name') }}"
      vars:
        fruits:
          apple:
            color: green
            size: big
          banana:
            color: yellow
            size: small

       gives:

       msg:
         - color: green
           name: apple
           size: big
         - color: yellow
           name: banana
           size: small

    Example 6:

    - name: Convert dictionary where NOT all values are dictionaries
            to a first item in a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits:
          apple:
            color: green
            size: big
          banana:
            color: yellow
            size: small
          orange: ripe

       gives:

       msg:
         - apple:
             color: green
             size: big
           banana:
             color: yellow
             size: small
           orange: ripe

    Example 7:

    - name: Convert dictionary where NOT all values are dictionaries
            to a first item in a list
      debug:
        msg: "{{ fruits|any2items }}"
      vars:
        fruits:
          apple: green
          banana: yellow
          orange: ripe

       gives:

       msg:
         - apple: green
           banana: yellow
           orange: ripe

    Example 8:

    - name: Iterate any data by any2items
      debug:
        var: item
      loop: "{{ [{'a': 1},{'b': 2}]|any2items }}"

    - name: Iterate any data by any2items
      debug:
        var: item
      loop: "{{ {'c': 3}|any2items }}"

    '''

    if not isinstance(key, string_types):
        raise AnsibleFilterError('Argument key for any2items must be string. %s is %s' %
                                 (key, type(key)))
    if not isinstance(override, bool):
        raise AnsibleFilterError('Argument override for any2items must be boollean. %s is %s' %
                                 (override, type(override)))

    if isinstance(x, Mapping):
        keys = list(x.keys())
        values = list(x.values())
        if all(isinstance(value, Mapping) for value in values):
            if (not override) and any(key in list(value.keys()) for value in values):
                raise AnsibleFilterError('Key %s present in the dictionary.' % (key))
            else:
                l =  values
                for idx, item in enumerate(values):
                   z = item.copy()
                   z.update({key: keys[idx]})
                   l[idx] = z
        else:
            l = []
            l.insert(0, x)
        return l
    elif isinstance(x, string_types):
        l = []
        l.insert(0, x)
        return l
    elif isinstance(x, Sequence):
        l = list(x)
        return l
    else:
        l = []
        l.insert(0, x)
        return l


def items2dict2(mylist, key_name='key', value_name='value', default_value=None):
    '''Takes a list of dicts with each having a 'key' and 'value' keys,
    and transforms the list into a dictionary, effectively as the
    reverse of dict2items. If 'value_name' does not exist use
    'default_value'.

    - name: Example 1
      debug:
        msg: "{{ fruits|items2dict2 }}"
      vars:
        fruits:
          - key: apple
            value: green
          - key: banana
          - key: orange

      msg:
        apple: green
        banana: null
        orange: null

    - name: Example 2
      debug:
        msg: "{{ fruits|items2dict2(key_name='k',
                                    value_name='v',
                                    default_value='undefined') }}"
      vars:
        fruits:
          - k: apple
            v: green
          - k: banana
          - k: orange

       gives:

       msg:
         apple: green
         banana: undefined
         orange: undefined
    '''

    if not isinstance(mylist, Sequence):
        raise AnsibleFilterError("First argument for community.general.items2dict2 requires a list. %s is %s" %
                                 (mylist, type(mylist)))

    return dict((item[key_name], item.setdefault(value_name, default_value)) for item in mylist)


class FilterModule(object):
    ''' Ansible list filters '''

    def filters(self):
        return {
            'lists_mergeby': lists_mergeby,
            'any2items': any2items,
            'items2dict2': items2dict2,
        }
