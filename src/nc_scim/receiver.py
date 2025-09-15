from fastapi import FastAPI, logger
from nc_scim.forwarder import UserAPI, GroupAPI
from scim2_models import User, Group, ListResponse, Resource
import json
from typing import Optional, Union, List

app = FastAPI()

@app.get('/Schemas')
def get_schemas(): ...


@app.get('/Users')
def get_all_users():
    all_users, _ = UserAPI.get_all()
    logger.logger.debug(all_users)

    scim_users: list = []
    for u in all_users:
        u_data, _ = UserAPI.get(u)
        scim_users.append(u_data)
    
    return scim_users


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

    elif attributes ==  'members':
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
        raise NotImplementedError(f'Adding the {attributes} attribute is not supported at this time. Only the "member" attribute is supported.')

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
