from typing import Annotated, Optional
from urllib.parse import parse_qs as parse_query_string
from urllib.parse import urlencode as encode_query_string

from fastapi import FastAPI
from fastapi.params import Query
from fastapi.responses import JSONResponse, Response
from scim2_models import (
    Bulk,
    ChangePassword,
    ETag,
    Filter,
    Group,
    ListResponse,
    Patch,
    PatchOp,
    ServiceProviderConfig,
    Sort,
    User,
)
from starlette.types import ASGIApp, Receive, Scope, Send

from nc_scim.forwarder import GroupAPI, NCJSONResponse, UserAPI
from nc_scim.mappings import group_nc_to_scim, user_nc_to_scim, user_scim_to_nc


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
            # fmt: off
            scope["query_string"] = encode_query_string(flattened, doseq=True).encode("utf-8")
            # fmt: on

        #     await self.app(scope, receive, send)
        # else:
        await self.app(scope, receive, send)


# Helper functions
def select_path_attr_last_parent(obj: User | Group, path_parts: list[str]):
    """
    Return the last parent in the given path.

    Examples
    --------
    - Object: User
    - Given path: `name.givenName`
    - Last parent: `name`
    """

    if len(path_parts) == 1:
        return obj

    last_parent = getattr(obj, path_parts[0])
    children = path_parts[1:]

    return select_path_attr_last_parent(last_parent, children)


app = FastAPI()
app.add_middleware(QueryStringFlatteningMiddleware)


# Users


@app.get("/Users")
def get_users(
    attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    excludedAttributes: Annotated[list, Query()] = [],
    filter: Optional[str] = None,  # TODO: need to work on this one
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
    for u in all_users[startIndex - 1 : count]:
        u_data, _ = UserAPI.get(u)
        transformed = user_nc_to_scim(
            u_data, attributes=attributes, excluded_attributes=excludedAttributes
        )
        scim_users.append(transformed)

    return ListResponse[User].model_validate(
        {"Resources": [u.model_dump() for u in scim_users]}
    )


@app.get("/Users/{user_id}")
def get_user_by_id(
    user_id: str,
    attributes: Annotated[list, Query()] = [],
    excludedAttributes: Annotated[list, Query()] = [],
):
    """Get the user with the specified user ID."""
    user, r = UserAPI.get(user_id)

    if r.status.is_error:
        return NCJSONResponse(r.status)

    return User.model_validate(
        user_nc_to_scim(
            user,
            attributes=["groups"] + attributes,
            excluded_attributes=excludedAttributes,
            all_attributes=True,
        )
    )


@app.post("/Users")
def create_user(data: User):
    nc_user = user_scim_to_nc(data)
    d, r = UserAPI.new(**nc_user)

    if r.status.is_error:
        return NCJSONResponse(r.status)

    return Response(status_code=201)


@app.delete("/Users/{user_id}")
def delete_user(user_id: str):
    # try:
    d, r = UserAPI.delete(user_id)

    if r.status.is_error:
        return NCJSONResponse(r.status)

    return Response(status_code=204)


# Groups


@app.get("/Groups")
def get_groups(
    attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    excludedAttributes: Annotated[list, Query()] = [],
    filter: Optional[str] = None,  # TODO: need to work on this one
    # sortBy: str = 'id',
    # sortOrder: Optional[SearchRequest.SortOrder] = None,
    startIndex: int = 1,
):
    # Get all groups
    all_groups, _ = GroupAPI.get()
    group_members: list[list[str]] = []

    if "members" in attributes:
        for gid in all_groups:
            gm, r = GroupAPI.get_members(gid)
            if r.status.is_error:
                return NCJSONResponse(r.status)
            group_members.append(gm)
    else:
        group_members = [[]] * len(all_groups)

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_groups)

    scim_groups: list[Group] = [
        group_nc_to_scim(
            gid,
            attributes=attributes,
            excluded_attributes=excludedAttributes,
            group_members=gm,
        )
        for gid, gm in zip(
            all_groups[startIndex - 1 : count], group_members[startIndex - 1 : count]
        )
    ]

    return ListResponse[Group].model_validate(
        {"Resources": [g.model_dump() for g in scim_groups]}
    )


@app.get("/Groups/{group_id}")
def get_group_by_id(
    group_id: str,
    attributes: Annotated[list, Query()] = ["members"],
    excludedAttributes: Annotated[list, Query()] = [],
):
    if "members" in attributes:
        members, r = GroupAPI.get_members(group_id)
        if r.status.is_error:
            return NCJSONResponse(r.status)

    scim_group = group_nc_to_scim(
        group_id,
        attributes=attributes,
        excluded_attributes=excludedAttributes,
        group_members=members if members else [],
        all_attributes=True,
    )

    return Group.model_validate(scim_group)


@app.post("/Groups")
def create_group(data: Group):
    if data.display_name is None:
        return JSONResponse(
            status_code=400,
            content={
                "message": "The `displayName` field is required for group creation."
            },
        )

    d, r = GroupAPI.new(data.display_name)
    if r.status.is_error:
        return NCJSONResponse(r.status)

    members, r = GroupAPI.get_members(data.display_name)
    if r.status.is_error:
        return NCJSONResponse(r.status)

    group = Group.model_validate(
        {"displayName": data.display_name, "id": data.display_name, "members": members}
    )
    return JSONResponse(status_code=201, content=group.model_dump())


@app.delete("/Groups/{group_id}")
def delete_group(group_id: str):
    d, r = GroupAPI.delete(group_id)
    if r.status.is_error:
        return NCJSONResponse(r.status)

    return Response(status_code=204)


@app.patch("/Groups/{group_id}")
def update_group_membership(group_id: str, data: PatchOp[Group]):
    assert data.operations is not None, "No operations given"
    assert data.operations[0].value is not None, "No users given"
    _users_raw: list[dict[str, str]] = data.operations[0].value

    if data.operations[0].path != "members":
        return JSONResponse(
            status_code=400,
            content={
                "message": "Only patching group membership is implemented at this time."
            },
        )

    match data.operations[0].op:
        case "add":
            for user in _users_raw:
                d, r = UserAPI.add_to_group(user["value"], group_id)

                if r.status.is_error:
                    return NCJSONResponse(r.status)

        case "remove":
            for user in _users_raw:
                d, r = UserAPI.remove_from_group(user["value"], group_id)
                if r.status.is_error:
                    return NCJSONResponse(r.status)

        case _:
            return JSONResponse(
                status_code=400,
                content={
                    "message": f"Unimplemented operation '{data.operations[0].op}'"
                },
            )

    return Response(status_code=204)


# Service Provider Config


@app.get("/ServiceProviderConfig")
def get_service_provider_config():
    return ServiceProviderConfig(
        sort=Sort(supported=False),
        etag=ETag(supported=False),
        bulk=Bulk(supported=False),
        change_password=ChangePassword(supported=False),
        patch=Patch(supported=True),
        filter=Filter(supported=False),
    )


@app.get("/Me")
@app.put("/Me")
@app.patch("/Me")
def me_unimplemented():
    return JSONResponse(
        status_code=404, content={"message": "The '/Me' endpoint is not implemented."}
    )


# if __name__ == "__main__":
#     all_groups, _ = GroupAPI.get()
#     print(
#         [
#             {
#                 "displayName": g,
#                 "id": g,
#                 "members": [
#                     {"value": member, "display": member}
#                     for member in GroupAPI.get_members(g)[0]
#                 ],
#             }
#             for g in all_groups
#         ]
#     )
#     print(GroupAPI.get_members('Standard Users')[0])
