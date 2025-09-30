from typing import Annotated, Any, Mapping, Optional
from urllib.parse import (
    parse_qs as parse_query_string,
    urlencode as encode_query_string,
)

from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.params import Query
from fastapi.responses import JSONResponse, Response
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from scim2_models import (
    Bulk,
    ChangePassword,
    Context,
    Error,
    ETag,
    Filter,
    Group as ScimGroup,
    ListResponse,
    Patch,
    PatchOp,
    ServiceProviderConfig,
    Sort,
    User as ScimUser,
)
from scim2_models.scim_object import ScimObject
from starlette.background import BackgroundTask
from starlette.types import ASGIApp, Receive, Scope, Send

from nc_scim import SCIM_TOKEN
from nc_scim.forwarder import GroupAPI, UserAPI
from nc_scim.models import NCGroup, NCUser


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
def select_path_attr_last_parent(obj: ScimUser | ScimGroup, path_parts: list[str]):
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


class UnauthorizedMessage(Error):
    detail: str = "Bearer token missing or unknown."
    status: int = 401


class ScimValidationError(Error):
    status: int = 422

    def __init__(self, exc: RequestValidationError):
        super().__init__(detail="\n".join([e["msg"] for e in exc.errors()]))


class ScimInternalServerError(Error):
    status: int = 500

    def __init__(self, exc: Exception):
        super().__init__(detail=f"Internal server error: '{exc}'")


class ScimHttpException(Error):
    def __init__(self, exc: HTTPException):
        super().__init__(status=exc.status_code, detail=exc.detail)


get_bearer_token = HTTPBearer(auto_error=False)


async def get_token(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(get_bearer_token),
) -> str:
    if auth is None or (token := auth.credentials) != SCIM_TOKEN:
        raise HTTPException(
            status_code=201,
            detail=UnauthorizedMessage().detail,
        )
    return token


# AnyPydanticModel = TypeVar('AnyPydanticModel', bound=BaseModel)


class ScimJsonResponse(JSONResponse):
    media_type = "application/scim+json"

    def __init__(
        self,
        content: ScimObject | BaseModel | dict[str, Any],
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ):
        if isinstance(content, ScimObject):
            content = content.model_dump(scim_ctx=Context.DEFAULT)
        elif isinstance(content, (NCUser, NCGroup)):
            content = content.to_scim().model_dump(scim_ctx=Context.DEFAULT)

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            background=background,
        )


class ScimContentlessResponse(Response):
    media_type = "application/scim+json"


app = FastAPI(separate_input_output_schemas=False)
app.add_middleware(QueryStringFlatteningMiddleware)


COMMON_API_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": UnauthorizedMessage},
    422: {"model": ScimValidationError},
    500: {"model": ScimInternalServerError},
}
COMMON_API_DEPENDENCIES = [Depends(get_token)]


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: ..., exc: RequestValidationError
):
    return ScimJsonResponse(status_code=422, content=ScimValidationError(exc))


@app.exception_handler(500)
async def internal_server_error_handler(request: ..., exc: Exception):
    return ScimJsonResponse(status_code=500, content=ScimInternalServerError(exc))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: ..., exc: HTTPException):
    return ScimJsonResponse(status_code=exc.status_code, content=ScimHttpException(exc))


# Users


@app.get(
    "/Users",
    response_class=ScimJsonResponse,
    response_model=ListResponse[ScimUser],
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
)
def get_users(
    attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    excludedAttributes: Annotated[list, Query()] = [],
    # filter: Optional[str] = None,  # TODO: need to work on this one
    # sortBy: str = 'id',
    # sortOrder: Optional[SearchRequest.SortOrder] = None,
    startIndex: int = 1,
    # token: str = Depends(get_token),
) -> ScimJsonResponse:
    # Get all users
    all_users = UserAPI.get_all()

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_users)

    scim_users: list[ScimUser] = []
    for u in all_users[startIndex - 1 : count]:
        u_data = UserAPI.get(u)
        scim_users.append(u_data.to_scim())

    out_data = ListResponse[ScimUser].model_validate(
        {"Resources": [u.model_dump() for u in scim_users]}
    )
    return ScimJsonResponse(
        status_code=200,
        content=out_data,
    )


@app.get(
    "/Users/{user_id}",
    response_class=ScimJsonResponse,
    response_model=ScimGroup,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
)
def get_user_by_id(
    user_id: str,
    attributes: Annotated[list, Query()] = [],
    excludedAttributes: Annotated[list, Query()] = [],
    token: str = Depends(get_token),
):
    """Get the user with the specified user ID."""
    user = UserAPI.get(user_id)

    return ScimJsonResponse(user)


@app.post(
    "/Users",
    response_model=ScimUser,
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
    status_code=201,
)
def create_user(
    data: ScimUser = Body(media_type="application/scim+json"),
    token: str = Depends(get_token),
):
    nc_user = NCUser.from_scim(data)
    UserAPI.new(nc_user)

    new = UserAPI.get(nc_user.id)

    return ScimJsonResponse(status_code=201, content=new)


@app.delete(
    "/Users/{user_id}",
    status_code=204,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
    response_class=ScimContentlessResponse,
)
def delete_user(
    user_id: str,
    token: str = Depends(get_token),
):
    UserAPI.delete(user_id)
    return ScimContentlessResponse(status_code=204)


# @app.patch(
#     "/Users/{user_id}",
#     dependencies=COMMON_API_DEPENDENCIES,
#     responses=COMMON_API_RESPONSES,
#     response_class=ScimJsonResponse,

# )
# def update_user_not_implemented(user_id: str, data: PatchOp[ScimUser]):
#     # return ScimJsonResponse(
#     #     status_code=405,
#     #     content="PATCH operations on users are currently not implemented. See README.md for details.",
#     # )
#     return HTTPException(status_code=405)


# Groups


@app.get(
    "/Groups",
    response_model=ListResponse[ScimGroup],
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
)
def get_groups(
    # attributes: Annotated[list, Query()] = [],
    count: Optional[int] = None,
    # excludedAttributes: Annotated[list, Query()] = [],
    # filter: Optional[str] = None,  # TODO: need to work on this one
    # sortBy: str = 'id',
    # sortOrder: Optional[SearchRequest.SortOrder] = None,
    startIndex: int = 1,
    token: str = Depends(get_token),
):
    # Get all groups
    all_group_ids = GroupAPI.get()

    # Set dynamic defaults of parameters
    if not count:
        count = len(all_group_ids)

    nc_groups: list[NCGroup] = [
        NCGroup.model_validate({"groupid": gid, "members": GroupAPI.get_members(gid)})
        for gid in all_group_ids[startIndex - 1 : count]
    ]

    scim_groups: list[ScimGroup] = [ncg.to_scim() for ncg in nc_groups]

    return ScimJsonResponse(
        # status_code=200,
        content=ListResponse[ScimGroup].model_validate(
            {"Resources": [g.model_dump() for g in scim_groups]}
        )
    )


@app.get(
    "/Groups/{group_id}",
    response_model=ScimGroup,
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
)
def get_group_by_id(
    group_id: str,
    # attributes: Annotated[list, Query()] = ["members"],
    # excludedAttributes: Annotated[list, Query()] = [],
    token: str = Depends(get_token),
):
    nc_group = NCGroup.model_validate(
        {
            "groupid": group_id,
            "members": GroupAPI.get_members(group_id),
        }
    )

    return ScimJsonResponse(content=nc_group)


@app.post(
    "/Groups",
    response_model=ScimGroup,
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
    status_code=201,
)
def create_group(
    data: ScimGroup = Body(media_type="application/scim+json"),
    token: str = Depends(get_token),
):
    if data.display_name is None:
        raise HTTPException(
            status_code=400,
            detail="The `displayName` field is required for group creation",
        )

    GroupAPI.new(data.display_name)
    members = GroupAPI.get_members(data.display_name)

    group = ScimGroup.model_validate(
        {
            "displayName": data.display_name,
            "id": data.display_name,
            "members": members,
        }
    )
    return ScimJsonResponse(status_code=201, content=group)


@app.delete(
    "/Groups/{group_id}",
    status_code=204,
    response_class=ScimContentlessResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
)
def delete_group(
    group_id: str,
    token: str = Depends(get_token),
):
    GroupAPI.delete(group_id)
    return ScimContentlessResponse(status_code=204)


@app.patch(
    "/Groups/{group_id}",
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
    response_model=ScimGroup,
)
def update_group_membership(
    group_id: str,
    data: PatchOp[ScimGroup] = Body(media_type="application/scim+json"),
    token: str = Depends(get_token),
):
    if not data.operations:
        raise HTTPException(status_code=400, detail="No operations given")

    for op in data.operations:
        if not op.value:
            raise HTTPException(status_code=400, detail="No users given")
        user_ids = [u["value"] for u in op.value]

        if op.path != "members":
            raise HTTPException(
                status_code=400,
                detail="Only patching group membership is implemented at this time",
            )

        match op.op:
            case "add":
                for uid in user_ids:
                    UserAPI.add_to_group(uid, group_id)

            case "remove":
                for uid in user_ids:
                    UserAPI.remove_from_group(uid, group_id)

            case _:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unimplemented operation '{data.operations[0].op}'",
                )

    group = NCGroup(groupid=group_id, members=GroupAPI.get_members(group_id))

    return ScimJsonResponse(status_code=200, content=group)


# Service Provider Config


@app.get(
    "/ServiceProviderConfig",
    response_class=ScimJsonResponse,
    dependencies=COMMON_API_DEPENDENCIES,
    responses=COMMON_API_RESPONSES,
    response_model=ServiceProviderConfig,
)
def get_service_provider_config(
    token: str = Depends(get_token),
):
    spc = ServiceProviderConfig(
        sort=Sort(supported=False),
        etag=ETag(supported=False),
        bulk=Bulk(supported=False),
        change_password=ChangePassword(supported=False),
        patch=Patch(supported=True),
        filter=Filter(supported=False),
    )
    return ScimJsonResponse(status_code=200, content=spc)


# @app.get("/Me", name="SCIM /Me endpoint - unimplemented")
# @app.put("/Me", name="SCIM /Me endpoint - unimplemented")
# @app.patch("/Me", name="SCIM /Me endpoint - unimplemented")
# def me_unimplemented(
#     token: str = Depends(get_token),
# ):
#     """SCIM /Me endpoint - unimplemented"""
#     return HTTPException(
#         status_code=404, detail="The '/Me' endpoint is not implemented."
#     )


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
