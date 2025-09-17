from __future__ import annotations

from typing import Any, Optional

import requests
import xmltodict

from nc_scim import NEXTCLOUD_BASEURL, NEXTCLOUD_SECRET, NEXTCLOUD_USERNAME

standard_headers = {"OCS-APIRequest": "true"}
post_headers = {**standard_headers, "Content-Type": "application/x-www-form-urlencoded"}


def url_assemble(path: str) -> str:
    protocol = "https"
    return f"{protocol}://{NEXTCLOUD_USERNAME}:{NEXTCLOUD_SECRET}@{NEXTCLOUD_BASEURL}{path}"


class NCAPIResponseError(ValueError):
    message: str
    nc_response: NCResponse

    def __init__(self, nc_response: Optional[NCResponse], message: str):
        super().__init__(message)
        self.message = message
        self.nc_response = nc_response  # type:ignore


class NCResponse:
    meta: dict[str, str]
    status: str
    status_code: int
    status_codes_mapping: dict[int, str]
    total_items: int
    items_per_page: int
    data: dict[str, Any]

    def __init__(
        self, http_response: requests.Response, status_codes: dict[int, str] = {}
    ):
        # self.raw_response = http_response
        http_response.raise_for_status()
        # fmt: off
        # self.raw_data = xmltodict.parse(str(
        #     http_response.content,
        #     encoding="utf-8"
        # ))["ocs"]
        self.raw_data = xmltodict.parse(http_response.text)["ocs"]
        # fmt: on

        self.data: dict[str, Any] = NCResponse._unwrap_element_key(
            self.raw_data["data"]
        )
        # if not self.data:
        #     raise NCAPIResponseError(self, "No data returned.")
        self.meta = self.raw_data["meta"]
        self.status = self.meta.get("status", "")
        self.status_code = int(self.meta.get("statuscode", 0))
        self.status_codes_mapping = status_codes
        self.message = self.meta.get("message", "")
        self.total_items = (
            int(v) if (v := self.meta.get("totalitems", 0)) is not None else 0
        )
        self.items_per_page = (
            int(v) if (v := self.meta.get("itemsperpage", 0)) is not None else 0
        )

    # Thanks, Copilot!
    @staticmethod
    def _unwrap_element_key(obj, key="element"):
        """
        Unwrap the given elemenet (defaults to `element`) in the dictionary.

        Example: `'data': {'users': {'element': ['user1', 'user2']}}` becomes `'data': {'users': ['user1', 'user2']}`
        """
        if isinstance(obj, dict):
            # If the dict has only the target key, unwrap it
            if list(obj.keys()) == [key]:
                return NCResponse._unwrap_element_key(obj[key], key)
            return {k: NCResponse._unwrap_element_key(v, key) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [NCResponse._unwrap_element_key(item, key) for item in obj]
        else:
            return obj

    def raise_for_ncapi_status(self):
        if self.status_code != 100:
            # raise requests.exceptions.HTTPError(response=self.raw_response)
            raise NCAPIResponseError(self, self.status_string)

    @property
    def status_string(self) -> str:
        return self.status_codes_mapping.get(self.status_code, "Unknown error")

    def serialize(self) -> dict:
        # fields = [
        #     a for a in dir(self)
        #     if not a.startswith('__')
        #      and not callable(getattr(self, a))
        # ]
        # return { k: getattr(self, k) for k in fields }
        return self.__dict__


class UserAPI:
    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#search-get-users
    @staticmethod
    def get_all() -> tuple[list[str], NCResponse]:
        r = NCResponse(
            requests.get(url_assemble("/users"), headers=standard_headers),
            status_codes={100: "success"},
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
            status_codes={
                100: "success",
                101: "invalid argument",
                102: "user already exists",
                103: "cannot create sub-admins for admin group",
                104: "group does not exist",
                105: "insufficient privileges for group",
                106: "no group specified (required for sub-admins)",
                107: "hint exceptions",
                108: "an email address is required, to send a password link to the user",
                109: "sub-admin group does not exist",
                110: "required email address was not provided",
                111: "could not create non-existing user ID",
            },
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#get-data-of-a-single-user
    @staticmethod
    def get(user_id: str) -> tuple[dict[str, Any], NCResponse]:
        r = NCResponse(
            requests.get(
                url_assemble(f"/users/{user_id}"),
                headers=standard_headers,
            ),
            status_codes={100: "success"},
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
                f"{key} is not a valid field name. Accepted fields: {', '.join(valid_fields)}"
            )

        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}"),
                headers=standard_headers,
                params={key: value},
            ),
            status_codes={
                100: "success",
                101: "invalid argument",
                107: "password policy (hint exception)",
                112: "setting the password is not supported by the users backend",
                113: "editing field not allowed or field doesn't exist",
            },
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#disable-a-user
    @staticmethod
    def disable(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}/disable"), headers=standard_headers
            ),
            status_codes={100: "successful", 101: "failure"},
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#enable-a-user
    @staticmethod
    def enable(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.put(
                url_assemble(f"/users/{user_id}/enable"), headers=standard_headers
            ),
            status_codes={100: "successful", 101: "failure"},
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html#delete-a-user
    @staticmethod
    def delete(user_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.delete(
                url_assemble(f"/users/{user_id}"), headers=standard_headers
            ),
            status_codes={100: "successful", 101: "failure"},
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
            status_codes={
                100: "successful",
                101: "no group specified",
                102: "group does not exist",
                103: "user does not exist",
                104: "insufficient privileges",
                105: "failed to add user to group",
            },
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
            status_codes={
                100: "successful",
                101: "no group specified",
                102: "group does not exist",
                103: "user does not exist",
                104: "insufficient privileges",
                105: "failed to remove user from group",
            },
        )
        return None, r


class GroupAPI:
    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#search-get-groups
    @staticmethod
    def get(group_id: Optional[str] = None) -> tuple[list[str], NCResponse]:
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
            status_codes={100: "success"},
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
            status_codes={
                100: "successful",
                101: "invalid input data",
                102: "group already exists",
                103: "failed to add the group",
            },
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#get-members-of-a-group
    @staticmethod
    def get_members(group_id: str) -> tuple[list[str], NCResponse]:
        r = NCResponse(
            requests.get(url_assemble(f"/groups/{group_id}"), headers=standard_headers),
            status_codes={100: "successful"},
        )
        if not (members := r.data["users"]):
            return [], r
        elif isinstance(members, str):
            return [members], r
        elif isinstance(members, list):
            return members, r
        else:
            raise TypeError("Group members are not of type None, str, or list")

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#edit-data-of-a-single-group
    @staticmethod
    def update(group_id: str, key: str, value: str) -> tuple[None, NCResponse]:
        valid_fields = ["displayname"]
        if key not in valid_fields:
            raise ValueError(
                f"{key} is not a valid field name. Accepted fields: {', '.join(valid_fields)}"
            )

        r = NCResponse(
            requests.put(
                url_assemble(f"/groups/{group_id}"),
                headers=standard_headers,
                params={key: value},
            ),
            status_codes={100: "successful", 101: "not supported by backend"},
        )
        return None, r

    # https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#delete-a-group
    @staticmethod
    def delete(group_id: str) -> tuple[None, NCResponse]:
        r = NCResponse(
            requests.delete(
                url_assemble(f"/groups/{group_id}"), headers=standard_headers
            ),
            status_codes={
                100: "successful",
                101: "group does not exist",
                102: "failed to delete group",
            },
        )
        return None, r


if __name__ == "__main__":
    import json

    print(json.dumps(GroupAPI.get()[0], indent=2))
