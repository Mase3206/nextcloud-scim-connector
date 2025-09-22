from __future__ import annotations

from typing import Any

import requests
import xmltodict
from fastapi.responses import JSONResponse

from nc_scim import (
    NEXTCLOUD_BASEURL,
    NEXTCLOUD_HTTPS,
    NEXTCLOUD_SECRET,
    NEXTCLOUD_USERNAME,
)

standard_headers = {"OCS-APIRequest": "true"}
post_headers = {**standard_headers, "Content-Type": "application/x-www-form-urlencoded"}


def url_assemble(path: str) -> str:
    protocol = "https" if NEXTCLOUD_HTTPS else "http"
    return f"{protocol}://{NEXTCLOUD_USERNAME}:{NEXTCLOUD_SECRET}@{NEXTCLOUD_BASEURL}{path}"


class NCStatusCode:
    nc: int
    http: int
    message: str

    def __init__(self, nc_code: int, http_code: int, message: str):
        self.nc = nc_code
        self.http = http_code
        self.message = message

    @property
    def is_error(self) -> bool:
        return self.nc != 100


class NCStatusCodeMapping:
    def __init__(self, code_mappings: list[NCStatusCode]):
        self.mappings = {cm.nc: cm for cm in code_mappings}

    def __getitem__(self, nc_code: int) -> NCStatusCode:
        try:
            return self.mappings[nc_code]
        except KeyError or KeyError:
            return NCStatusCode(0, 500, "Unknown error")


class NCJSONResponse(JSONResponse):
    def __init__(
        self,
        status_code: NCStatusCode,
    ) -> None:
        super().__init__(
            status_code=status_code.http,
            content={"detail": status_code.message},
        )


class NCResponse:
    meta: dict[str, str]
    status: NCStatusCode
    # status_code: int
    status_codes_mapping: NCStatusCodeMapping
    total_items: int
    items_per_page: int
    data: dict[str, Any]

    def __init__(
        self,
        http_response: requests.Response,
        status_code_mapping: NCStatusCodeMapping | list[NCStatusCode],
    ):
        http_response.raise_for_status()

        if not isinstance(status_code_mapping, NCStatusCodeMapping):
            self.status_codes_mapping = NCStatusCodeMapping(status_code_mapping)

        self.raw_data = xmltodict.parse(http_response.text)["ocs"]

        self.data: dict[str, Any] = NCResponse._unwrap_element_key(
            self.raw_data["data"],
        )

        self.meta = self.raw_data["meta"]
        self.status = self.status_codes_mapping[int(self.meta.get("statuscode", 0))]
        self.total_items = (
            int(v) if (v := self.meta.get("totalitems", 0)) is not None else 0
        )
        self.items_per_page = (
            int(v) if (v := self.meta.get("itemsperpage", 0)) is not None else 0
        )

    # Thanks, Copilot!
    @staticmethod
    def _unwrap_element_key(obj, key="element"):
        """Unwrap the given elemenet (defaults to `element`) in the dictionary.

        Example: `'data': {'users': {'element': ['user1', 'user2']}}` becomes `'data': {'users': ['user1', 'user2']}`
        """
        if isinstance(obj, dict):
            # If the dict has only the target key, unwrap it
            if list(obj.keys()) == [key]:
                return NCResponse._unwrap_element_key(obj[key], key)
            return {k: NCResponse._unwrap_element_key(v, key) for k, v in obj.items()}
        if isinstance(obj, list):
            return [NCResponse._unwrap_element_key(item, key) for item in obj]
        return obj

    def serialize(self) -> dict:
        return self.__dict__


class UserAPI:
    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#search-get-users
    @staticmethod
    def get_all() -> tuple[list[str], NCResponse]:
        r = NCResponse(
            requests.get(url_assemble("/users"), headers=standard_headers),
            status_code_mapping=[NCStatusCode(100, 200, "Success")],
        )
        return r.data["users"], r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#add-a-new-user
    @staticmethod
    def new(
        user_id: str,
        display_name: str,
        email: str,
        groups: list[str] = [],
        password: str = "This is not set by SCIM.",
        subadmin_groups: list[str] = [],
        quota: str = "",
        language: str = "en",
        enabled: bool = True,
    ) -> tuple[None, NCResponse]:
        # fmt: off
        r = NCResponse(
            requests.post(
                url_assemble("/users"),
                headers=post_headers,
                data={
                    "userid": user_id,
                    "displayName": display_name,
                    "email": email,
                    "groups": groups,
                    "password": password,
                    "subadmin": subadmin_groups,
                    "quota": quota,
                    "language": language,
                },
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "success"),
                NCStatusCode(101, 400, "invalid argument"),
                NCStatusCode(102, 409, "user already exists"),
                NCStatusCode(103, 400, "cannot create sub-admins for admin group"),
                NCStatusCode(104, 404, "group does not exist"),
                NCStatusCode(105, 403, "insufficient privileges for group"),
                NCStatusCode(106, 400, "no group specified (required for sub-admins)"),
                NCStatusCode(107, 400, "hint exceptions"),
                NCStatusCode(108, 400, "an email address is required, to send a password link to the user"),
                NCStatusCode(109, 404, "sub-admin group does not exist"),
                NCStatusCode(110, 400, "required email address was not provided"),
                NCStatusCode(111, 400, "could not create non-existing user ID"),
            ],
        )
        # fmt: on
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#get-data-of-a-single-user
    @staticmethod
    def get(user_id: str) -> tuple[dict[str, Any], NCResponse]:
        r = NCResponse(
            requests.get(
                url_assemble(f"/users/{user_id}"),
                headers=standard_headers,
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "success"),
                NCStatusCode(404, 404, "user does not exist"),
            ],
        )

        return r.data, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#edit-data-of-a-single-user
    @staticmethod
    def update(user_id: str, key: str, value: str) -> tuple[None, NCResponse]:
        valid_fields = [
            "email",
            "quota",
            "displayname",
            "display",
            "phone",
            "address",
            "website",
            "twitter",
            "password",
        ]
        if key not in valid_fields:
            raise ValueError(
                f"{key} is not a valid field name. Accepted fields: {', '.join(valid_fields)}",
            )

        # fmt: off
        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}"),
                headers=standard_headers,
                params={key: value},
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "success"),
                NCStatusCode(101, 400, "invalid argument"),
                NCStatusCode(107, 400, "password policy (hint exception)"),
                NCStatusCode(112, 400, "setting the password is not supported by the users backend"),
                NCStatusCode(113, 400, "editing field not allowed or field doesn't exist"),
            ],
        )
        # fmt: on
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#disable-a-user
    @staticmethod
    def disable(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}/disable"),
                headers=standard_headers,
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 500, "failure"),
            ],
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#enable-a-user
    @staticmethod
    def enable(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}/enable"),
                headers=standard_headers,
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 500, "failure"),
            ],
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#delete-a-user
    @staticmethod
    def delete(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.delete(
                url_assemble(f"/users/{user_id}"),
                headers=standard_headers,
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 500, "failure"),
                NCStatusCode(998, 404, "user does not exist"),
            ],
        )
        return None, r
        # raise NotImplementedError(
        #     "Deleting users via the SCIM connector and provisioning API is currently considered unsafe and is not supported at this time."
        # )

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#get-user-s-groups
    @staticmethod
    def get_groups(user_id: str) -> tuple[list[str], NCResponse]:
        u, r = UserAPI.get(user_id)
        return u["groups"], r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#get-user-s-groups
    @staticmethod
    def add_to_group(user_id: str, group_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.post(
                url_assemble(f"/users/{user_id}/groups"),
                headers=post_headers,
                data={"groupid": group_id},
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 400, "no group specified"),
                NCStatusCode(102, 404, "group does not exist"),
                NCStatusCode(103, 404, "user does not exist"),
                NCStatusCode(104, 403, "insufficient privileges"),
                NCStatusCode(105, 500, "failed to add user to group"),
            ],
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#remove-user-from-group
    @staticmethod
    def remove_from_group(user_id: str, group_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.delete(
                url_assemble(f"/users/{user_id}/groups"),
                headers=post_headers,
                params={"groupid": group_id},
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 400, "no group specified"),
                NCStatusCode(102, 404, "group does not exist"),
                NCStatusCode(103, 404, "user does not exist"),
                NCStatusCode(104, 403, "insufficient privileges"),
                NCStatusCode(105, 500, "failed to remove user from group"),
            ],
        )
        return None, r


class GroupAPI:
    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#search-get-groups
    @staticmethod
    def get(group_id: str | None = None) -> tuple[list[str], NCResponse]:
        r = NCResponse(
            (
                requests.get(url_assemble("/groups"), headers=standard_headers)
                if not group_id
                else requests.get(
                    url_assemble("/groups"),
                    headers=standard_headers,
                    params={"search": group_id},
                )
            ),
            status_code_mapping=[NCStatusCode(100, 200, "success")],
        )
        return r.data["groups"], r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#create-a-group
    @staticmethod
    def new(group_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.post(
                url_assemble("/groups"),
                headers=post_headers,
                data={"groupid": group_id},
            ),
            status_code_mapping=[
                NCStatusCode(100, 201, "successful"),
                NCStatusCode(101, 400, "invalid input data"),
                NCStatusCode(102, 409, "group already exists"),
                NCStatusCode(103, 500, "failed to add the group"),
            ],
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#get-members-of-a-group
    @staticmethod
    def get_members(group_id: str) -> tuple[list[str], NCResponse]:
        r = NCResponse(
            requests.get(url_assemble(f"/groups/{group_id}"), headers=standard_headers),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(404, 404, "group does not exist"),
            ],
        )
        if not r.data or not (members := r.data.get("users", [])):
            return [], r
        if isinstance(members, str):
            return [members], r
        if isinstance(members, list):
            return members, r
        raise TypeError("Group members are not of type None, str, or list")

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#edit-data-of-a-single-group
    @staticmethod
    def update(group_id: str, key: str, value: str) -> tuple[None, NCResponse]:
        valid_fields = ["displayname"]
        if key not in valid_fields:
            raise ValueError(
                f"{key} is not a valid field name. Accepted fields: {', '.join(valid_fields)}",
            )

        r = NCResponse(
            requests.put(
                url_assemble(f"/groups/{group_id}"),
                headers=standard_headers,
                params={key: value},
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 500, "not supported by backend"),
            ],
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#delete-a-group
    @staticmethod
    def delete(group_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.delete(
                url_assemble(f"/groups/{group_id}"),
                headers=standard_headers,
            ),
            status_code_mapping=[
                NCStatusCode(100, 200, "successful"),
                NCStatusCode(101, 404, "group does not exist"),
                NCStatusCode(102, 500, "failed to delete group"),
            ],
        )
        return None, r


if __name__ == "__main__":
    import json

    print(json.dumps(GroupAPI.get()[0], indent=2))
