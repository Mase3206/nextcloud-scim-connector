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

from nc_scim.forwarder import GroupAPI, NCAPIResponseError, UserAPI
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
    user, _ = UserAPI.get(user_id)
    if user is None:
        return JSONResponse(
            status_code=404, content={"message": f"User '{user_id}' does not exist."}
        )
    # return PlainTextResponse(f'"{user == None}"')
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
    try:
        UserAPI.new(**nc_user)[1].raise_for_ncapi_status()
    except NCAPIResponseError as e:
        if e.nc_response.status_code == 102:
            return JSONResponse(
                status_code=409,
                content={
                    "message": f"User '{nc_user['user_id']}' already exists",
                    "nc_status_code": e.nc_response.status_code,
                },
            )
        elif e.nc_response.status_code >= 101 and e.nc_response.status_code <= 111:
            return JSONResponse(
                status_code=400,
                content={
                    "message": e.message,
                    "nc_status_code": e.nc_response.status_code,
                },
            )
    return Response(status_code=201)


@app.delete("/Users/{user_id}")
def delete_user(user_id: str):
    try:
        UserAPI.delete(user_id)[1].raise_for_ncapi_status()
    except NCAPIResponseError as e:
        if e.nc_response.status_code == 998:
            return JSONResponse(
                status_code=404,
                content={
                    "message": f"User '{user_id}' does not exist",
                    "nc_status_code": e.nc_response.status_code,
                },
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "message": "Unknown error",
                    "nc_response": e.nc_response.serialize(),
                },
            )
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

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_groups)

    scim_groups: list[Group] = [
        group_nc_to_scim(
            g, attributes=attributes, excluded_attributes=excludedAttributes
        )
        for g in all_groups[startIndex - 1 : count]
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
    d = GroupAPI.get_members(group_id)
    d[1].raise_for_ncapi_status()

    scim_group = group_nc_to_scim(
        group_id, attributes=attributes, excluded_attributes=excludedAttributes
    )

    return Group.model_validate(scim_group)


@app.patch("/Groups/{group_id}")
def add_users_to_group(group_id: str, data: PatchOp[Group]):
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
            try:
                for user in _users_raw:
                    d, r = UserAPI.add_to_group(user["value"], group_id)
                    r.raise_for_ncapi_status()
                    # if not r.data:
                    #     raise NCAPIResponseError(r, 'no data')
            except NCAPIResponseError as e:
                # raise e
                match e.nc_response.status_code:
                    case 101:
                        return JSONResponse(
                            status_code=400, content={"message": e.message}
                        )
                    case 102, 103:
                        return JSONResponse(
                            status_code=404, content={"message": e.message}
                        )
                    case 104:
                        return JSONResponse(
                            status_code=403, content={"message": e.message}
                        )
                    case 105, _:
                        return JSONResponse(
                            status_code=500, content={"message": e.message}
                        )
        case "remove":
            try:
                for user in _users_raw:
                    d, r = UserAPI.remove_from_group(user["value"], group_id)
                    r.raise_for_ncapi_status()
            except NCAPIResponseError as e:
                match e.nc_response.status_code:
                    case 101:
                        return JSONResponse(
                            status_code=400, content={"message": e.message}
                        )
                    case 102, 103:
                        return JSONResponse(
                            status_code=404, content={"message": e.message}
                        )
                    case 104:
                        return JSONResponse(
                            status_code=403, content={"message": e.message}
                        )
                    case 105, _:
                        return JSONResponse(
                            status_code=500, content={"message": e.message}
                        )
        case _:
            return JSONResponse(
                status_code=400,
                content={
                    "message": f"Unimplemented operation '{data.operations[0].op}'"
                },
            )

    return Response(status_code=200)


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
