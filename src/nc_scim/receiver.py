from fastapi import FastAPI, logger
from nc_scim.forwarder import UserAPI, GroupAPI
from nc_scim.mappings import user_nc_to_scim, group_nc_to_scim
from scim2_models import User, Group, ListResponse
import json
from typing import Optional, Union, List, Annotated
from fastapi.params import Query, Depends


from starlette.types import ASGIApp, Scope, Receive, Send
from urllib.parse import parse_qs as parse_query_string
from urllib.parse import urlencode as encode_query_string

class QueryStringFlatteningMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        query_string = scope.get("query_string", None).decode()
        if scope["type"] == "http" and query_string:
            parsed = parse_query_string(query_string)
            flattened = {}
            for name, values in parsed.items():
                all_values = []
                for value in values:
                    all_values.extend(value.split(","))

                flattened[name] = all_values

            # doseq: Turn lists into repeated parameters, which is better for FastAPI
            scope["query_string"] = encode_query_string(flattened, doseq=True).encode("utf-8")

            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


app = FastAPI()
app.add_middleware(QueryStringFlatteningMiddleware)


@app.get('/Schemas')
def get_schemas(): ...


@app.get('/Users')
def get_all_users(attributes: Annotated[list, Query()] = []):
    all_users, _ = UserAPI.get_all()
    logger.logger.debug(all_users)

    # if not attributes:
    #     fetch_groups = False
    # elif 'groups' in attributes:
    #     fetch_groups = True
    # else:
    #     raise NotImplementedError(f'Adding the {type(attributes)} attribute is not supported at this time. Only the "groups" attribute is supported.')

    scim_users: list[User] = []
    for u in all_users:
        u_data, _ = UserAPI.get(u)
        transformed = user_nc_to_scim(
            u_data,
            attributes
        )
        scim_users.append(transformed)
    
    return ListResponse[User].model_validate({
        'Resources': [u.model_dump() for u in scim_users]
    })


@app.get('/Groups')
def get_all_groups(attributes: Annotated[list, Query()] = []):
    all_groups, _ = GroupAPI.get_all()
    logger.logger.info(attributes)

    scim_groups: list[Group] = [
        group_nc_to_scim(
            g, 
            attributes
        ) for g in all_groups
    ]

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
