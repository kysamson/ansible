#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: mso_schema_template_bd
short_description: Manage Bridge Domains (BDs) in schema templates
description:
- Manage BDs in schema templates on Cisco ACI Multi-Site.
author:
- Dag Wieers (@dagwieers)
version_added: '2.8'
options:
  schema:
    description:
    - The name of the schema.
    type: str
    required: yes
  template:
    description:
    - The name of the template.
    type: list
  bd:
    description:
    - The name of the BD to manage.
    type: str
    aliases: [ name ]
  display_name:
    description:
    - The name as displayed on the MSO web interface.
    type: str
  vrf:
    description:
    - The VRF associated to this ANP.
    type: str
  subnets:
    description:
    - The subnets associated to this ANP.
    type: list
    suboptions:
      ip:
        description:
        - The IP range in CIDR notation.
        type: str
        required: true
      description:
        description:
        - The description of this subnet.
        type: str
      scope:
        description:
        - The scope of the subnet.
        type: str
        choices: [ private, public ]
      shared:
        description:
        - Whether this subnet is shared between VRFs.
        type: bool
      no_default_gateway:
        description:
        - Whether this subnet has a default gateway.
        type: bool
  intersite_bum_traffic:
    description:
    - Whether to allow intersite BUM traffic.
    type: bool
  optimize_wan_bandwidth:
    description:
    - Whether to optimize WAN bandwidth.
    type: bool
  layer2_stretch:
    description:
    - Whether to enable L2 stretch.
    type: bool
  layer2_unknown_unicast:
    description:
    - Layer2 unknown unicast.
    type: str
    choices: [ flood, proxy ]
  layer3_multicast:
    description:
    - Whether to enable L3 multicast.
    type: bool
  state:
    description:
    - Use C(present) or C(absent) for adding or removing.
    - Use C(query) for listing an object or multiple objects.
    type: str
    choices: [ absent, present, query ]
    default: present
extends_documentation_fragment: mso
'''

EXAMPLES = r'''
- name: Add a new BD
  mso_schema_template_bd:
    host: mso_host
    username: admin
    password: SomeSecretPassword
    schema: Schema 1
    template: Template 1
    bd: BD 1
    state: present
  delegate_to: localhost

- name: Remove an BD
  mso_schema_template_bd:
    host: mso_host
    username: admin
    password: SomeSecretPassword
    schema: Schema 1
    template: Template 1
    bd: BD1
    state: absent
  delegate_to: localhost

- name: Query a specific BDs
  mso_schema_template_bd:
    host: mso_host
    username: admin
    password: SomeSecretPassword
    schema: Schema 1
    template: Template 1
    bd: BD1
    state: query
  delegate_to: localhost
  register: query_result

- name: Query all BDs
  mso_schema_template_bd:
    host: mso_host
    username: admin
    password: SomeSecretPassword
    schema: Schema 1
    template: Template 1
    state: query
  delegate_to: localhost
  register: query_result
'''

RETURN = r'''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.aci.mso import MSOModule, mso_argument_spec, mso_reference_spec, mso_subnet_spec


def main():
    argument_spec = mso_argument_spec()
    argument_spec.update(
        schema=dict(type='str', required=True),
        template=dict(type='str', required=True),
        bd=dict(type='str', required=False, aliases=['name']),  # This parameter is not required for querying all objects
        display_name=dict(type='str'),
        intersite_bum_traffic=dict(type='bool'),
        optimize_wan_bandwidth=dict(type='bool'),
        layer2_stretch=dict(type='bool'),
        layer2_unknown_unicast=dict(type='str', choices=['flood', 'proxy']),
        layer3_multicast=dict(type='bool'),
        vrf=dict(type='dict', options=mso_reference_spec()),
        subnets=dict(type='list', options=mso_subnet_spec()),
        state=dict(type='str', default='present', choices=['absent', 'present', 'query']),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'absent', ['bd']],
            ['state', 'present', ['bd', 'vrf']],
        ],
    )

    schema = module.params['schema']
    template = module.params['template']
    bd = module.params['bd']
    display_name = module.params['display_name']
    intersite_bum_traffic = module.params['intersite_bum_traffic']
    optimize_wan_bandwidth = module.params['optimize_wan_bandwidth']
    layer2_stretch = module.params['layer2_stretch']
    layer2_unknown_unicast = module.params['layer2_unknown_unicast']
    layer3_multicast = module.params['layer3_multicast']
    vrf = module.params['vrf']
    subnets = module.params['subnets']
    state = module.params['state']

    mso = MSOModule(module)

    # Get schema_id
    schema_obj = mso.get_obj('schemas', displayName=schema)
    if schema_obj:
        schema_id = schema_obj['id']
    else:
        mso.fail_json(msg="Provided schema '{0}' does not exist".format(schema))

    path = 'schemas/{id}'.format(id=schema_id)

    # Get template
    templates = [t['name'] for t in schema_obj['templates']]
    if template not in templates:
        mso.fail_json(msg="Provided template '{0}' does not exist. Existing templates: {1}".format(template, ', '.join(templates)))
    template_idx = templates.index(template)

    # Get ANP
    bds = [b['name'] for b in schema_obj['templates'][template_idx]['bds']]

    if bd is not None and bd in bds:
        bd_idx = bds.index(bd)
        mso.existing = schema_obj['templates'][template_idx]['bds'][bd_idx]

    if state == 'query':
        if bd is None:
            mso.existing = schema_obj['templates'][template_idx]['bds']
        elif not mso.existing:
            mso.fail_json(msg="BD '{bd}' not found".format(bd=bd))
        mso.exit_json()

    mso.previous = mso.existing
    if state == 'absent':
        if mso.existing:
            mso.sent = mso.existing = {}
            operation = [dict(
                op='remove',
                path='/templates/{template}/bds/{bd}'.format(template=template, bd=bd),
            )]
            if not module.check_mode:
                mso.request(path, method='PATCH', data=operation)

    elif state == 'present':
        vrf_ref = mso.make_reference(vrf, 'vrf', schema_id, template)
        subnets = mso.make_subnets(subnets)

        if display_name is None and not mso.existing:
            display_name = bd

        payload = dict(
            name=bd,
            displayName=display_name,
            intersiteBumTraffic=intersite_bum_traffic,
            optimizeWanBandwidth=optimize_wan_bandwidth,
            l2UnknownUnicast=layer2_unknown_unicast,
            l2Stretch=layer2_stretch,
            l3MCast=layer3_multicast,
            subnets=subnets,
            vrfRef=vrf_ref,
        )

        mso.sanitize(payload, collate=True, unwanted=['bdRef', 'vrfRef'])

        if mso.existing:
            operation = [dict(
                op='replace',
                path='/templates/{template}/bds/{bd}'.format(template=template, bd=bd),
                value=mso.sent,
            )]

        else:
            operation = [dict(
                op='add',
                path='/templates/{template}/bds/-'.format(template=template),
                value=mso.sent,
            )]

        mso.existing = mso.proposed
        if not module.check_mode:
            mso.request(path, method='PATCH', data=operation)

    mso.exit_json()


if __name__ == "__main__":
    main()
