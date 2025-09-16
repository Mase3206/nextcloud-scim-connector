from fastapi import FastAPI, logger
from nc_scim.forwarder import UserAPI, GroupAPI
from nc_scim.mappings import user_nc_to_scim, group_nc_to_scim
from scim2_models import User, Group, ListResponse, Sort, ServiceProviderConfig, ETag, Bulk, ChangePassword, Patch, Filter
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


# @app.get('/Schemas')
# def get_schemas(): ...


@app.get('/Users')
def get_users(
    attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    excludedAttributes: Annotated[list, Query()] = [],
    filter: Optional[str] = None, # TODO: need to work on this one
    # sortBy: str = 'id',
    # sortOrder: Optional[SearchRequest.SortOrder] = None,
    startIndex: int = 1,
):
    # Get all users
    all_users, _ = UserAPI.get_all()

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_users)
    

    scim_users: list[User] = []
    for u in all_users[startIndex-1:count]:
        u_data, _ = UserAPI.get(u)
        transformed = user_nc_to_scim(
            u_data,
            attributes=attributes,
            excluded_attributes=excludedAttributes
        )
        scim_users.append(transformed)

    # scim_users = list(sorted(
    #     scim_users,
    #     key = lambda u: str(getattr(u, sortBy)),
    #     reverse = (sortOrder == SearchRequest.SortOrder.descending)
    # ))
    

    return ListResponse[User].model_validate({
        'Resources': [u.model_dump() for u in scim_users]
    })





@app.get('/Groups')
def get_groups(
    attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    excludedAttributes: Annotated[list, Query()] = [],
    filter: Optional[str] = None, # TODO: need to work on this one
    # sortBy: str = 'id',
    # sortOrder: Optional[SearchRequest.SortOrder] = None,
    startIndex: int = 1,
):
    # Get all groups
    all_groups, _ = GroupAPI.get_all()

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_groups)


    scim_groups: list[Group] = [
        group_nc_to_scim(
            g,
            attributes=attributes,
            excluded_attributes=excludedAttributes
        ) for g in all_groups[startIndex-1:count]
    ]

    return ListResponse[Group].model_validate({
        'Resources': [g.model_dump() for g in scim_groups]
    })




@app.get('/ServiceProviderConfig')
def get_service_provider_config():
    return ServiceProviderConfig(
        sort = Sort(supported=False),
        etag = ETag(supported=False),
        bulk = Bulk(supported=False),
        change_password = ChangePassword(supported=False),
        patch = Patch(supported=False),
        filter = Filter(supported=False),
    )




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
