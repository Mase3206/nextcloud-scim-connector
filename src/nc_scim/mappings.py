# from nc_scim.forwarder import UserAPI
from scim2_models import User as ScimUser, Name, GroupMembership
from typing import Optional, Any

# class User(ScimUser):
#     def __init__(self, enabled: Optional[bool], id: Optional[str], displayname: Optional[str], *args, **kwargs):
#         self.active = enabled
#         self.user_name = id
#         self.display_name = displayname
#         # self.name = Name(formatted=displayname)
#         super().__init__(*args, **kwargs)


def to_scim_user(nc_user: dict[str, Any]) -> ScimUser:
    scim_user = {}

    if (is_active := nc_user.get('enabled', None)) is not None:
        scim_user['active'] = is_active

    scim_user['userName'] = nc_user['id']
    
    if (groups := nc_user.get('groups', None)) is None:
        scim_user['groups'] = []
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

    scim_user['emails'] = [{
        'value': nc_user['email'],
        'type': 'other',
        'primary': True
    }]

    scim_user['name'] = {
        'formatted': nc_user['displayname']
    }
    scim_user['displayName'] = nc_user['displayname']

    return ScimUser.model_validate(scim_user)
    

def to_nc_user(scim_user: ScimUser):
    # Editable fields
    # displayname
    # email
    # phone
    # address
    # website
    # twitter
    nc_user = {
        'enabled': scim_user.active,
        'id': scim_user.id,
        # 'displayname'
    }



if __name__ == '__main__':
    import json
    from pathlib import Path
    
    with open(Path('.').resolve() / 'sample' / 'sample.json', 'r') as f:
        sample_data: dict[str, list[dict[str, Any]]] = json.load(f)
    
    nc_users = sample_data['users']
    scim_users: list[ScimUser] = []
    for u in nc_users:
        scim_users.append(to_scim_user(u))

    for u in scim_users:
        print(json.dumps(u.model_dump(), indent=2), end='\n\n')

