from fastapi import FastAPI, logger
from nc_scim.forwarder import UserAPI, GroupAPI
from nc_scim.mappings import transform_nc_user_to_scim
from scim2_models import User, Group, ListResponse
import json
from typing import Optional, Union, List

app = FastAPI()

@app.get('/Schemas')
def get_schemas(): ...


@app.get('/Users')
def get_all_users(attributes: str | None = None):
    all_users, _ = UserAPI.get_all()
    logger.logger.debug(all_users)

    if not attributes:
        fetch_groups = False
    elif attributes == 'groups':
        fetch_groups = True
    else:
        raise NotImplementedError(f'Adding the {attributes} attribute is not supported at this time. Only the "groups" attribute is supported.')

    scim_users: list[User] = []
    for u in all_users:
        u_data, _ = UserAPI.get(u)
        transformed = transform_nc_user_to_scim(
            u_data,
            minimal = fetch_groups,
            attach_groups = fetch_groups,
        )
        scim_users.append(transformed)
    
    return ListResponse[User].model_validate({
        'Resources': [u.model_dump() for u in scim_users]
    })


@app.get('/Groups')
def get_all_groups(attributes: str | None = None):
    all_groups, _ = GroupAPI.get_all()
    logger.logger.info(attributes)

    if not attributes:
        scim_groups: list[Group] = [
            Group.model_validate({
                'displayName': g,
                'id': g
            }) for g in all_groups
        ]

    elif attributes == 'members':
        scim_groups: list[Group] = [
            Group.model_validate({
                'displayName': g,
                'id': g,
                'members': [
                    {
                        'value': member,
                        'display': member
                    } for member in GroupAPI.get_members(g)[0]
                ]
            }) for g in all_groups
        ]

    else:
        raise NotImplementedError(f'Adding the {attributes} attribute is not supported at this time. Only the "members" attribute is supported.')

    return ListResponse[Group].model_validate({
        'Resources': [g.model_dump() for g in scim_groups]
    })


if __name__ == '__main__':
    all_groups, _ = GroupAPI.get_all()
    print([
        {
            'displayName': g,
            'id': g,
            'members': [
                {
                    'value': member,
                    'display': member
                } for member in GroupAPI.get_members(g)[0]
            ]
        } for g in all_groups
    ])
    # print(GroupAPI.get_members('Standard Users')[0])
