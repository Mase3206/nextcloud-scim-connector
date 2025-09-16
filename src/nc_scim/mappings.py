# from nc_scim.forwarder import UserAPI
from scim2_models import User as ScimUser, Name, GroupMembership, Email
from typing import Optional, Any


def transform_nc_user_to_scim(nc_user: dict[str, Any], minimal: bool = False, attach_groups: bool = False) -> ScimUser:
    scim_user = {}

    scim_user['userName'] = nc_user['id']
    scim_user['id'] = nc_user['id']
    
    if attach_groups:
        if (groups := nc_user.get('groups', None)) is None:
            scim_user['groups'] = []
            # pass
        elif isinstance(groups, str):
            scim_user['groups'] = [GroupMembership(
                display=groups, 
                type='direct', 
                value=groups,
                ref=None
            )]
        elif isinstance(groups, list):
            scim_user['groups'] = [
                GroupMembership(
                    display=g,
                    type='direct',
                    value=g,
                    ref=None
                ) for g in groups
            ]

    if not minimal:
        if (is_active := nc_user.get('enabled', None)) is not None:
            scim_user['active'] = is_active

        scim_user['emails'] = [Email.model_validate({
            'value': nc_user['email'],
            'type': 'other',
            'primary': True
        })]

        scim_user['name'] = Name.model_validate({
            'formatted': nc_user['displayname']
        })
        scim_user['displayName'] = nc_user['displayname']

    return ScimUser.model_validate(scim_user)
    

def transform_scim_user_to_nc(scim_user: ScimUser) -> dict[str, Any]:
    # Editable fields
    # displayname
    # email
    # phone
    # address
    # website
    # twitter
    nc_user = {
        'enabled': scim_user.active,
        'id': scim_user.user_name,
        'displayname': scim_user.display_name,
        'email': e[0].value if (e := scim_user.emails) else None,
    }
    return nc_user



if __name__ == '__main__':
    import json
    from pathlib import Path
    
    with open(Path('.').resolve() / 'sample' / 'users.json', 'r') as f:
        sample_data: dict[str, list[dict[str, Any]]] = json.load(f)
    
    nc_users = sample_data['users']
    scim_users: list[ScimUser] = []
    for u in nc_users:
        scim_users.append(transform_nc_user_to_scim(u))

    for u in scim_users:
        print(json.dumps(u.model_dump(), indent=2))
        print(json.dumps(transform_scim_user_to_nc(u), indent=2), end='\n\n')
