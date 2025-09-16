# from nc_scim.forwarder import UserAPI
from typing import Any, Optional

from scim2_models import Email, Group, GroupMember, GroupMembership, Name, User

from nc_scim.forwarder import GroupAPI


def user_nc_to_scim(
    nc_user: dict[str, Any],
    attributes: list[str] = [],
    excluded_attributes: list[str] = ["groups"],
    all_attributes: Optional[bool] = None,
) -> User:
    # if all_attributes == None:
    #     all_attributes = not attributes  # if no attributes are passed
    scim_user = {}

    scim_user["userName"] = nc_user["id"]
    scim_user["id"] = nc_user["id"]

    # Groups are not given by default, as that is typically how SCIM is implemented.
    if "groups" in attributes and "groups" not in excluded_attributes:
        if (groups := nc_user.get("groups", None)) is None:
            scim_user["groups"] = []
            # pass
        elif isinstance(groups, str):
            scim_user["groups"] = [
                GroupMembership(display=groups, type="direct", value=groups, ref=None)
            ]
        elif isinstance(groups, list):
            scim_user["groups"] = [
                GroupMembership(display=g, type="direct", value=g, ref=None)
                for g in groups
            ]

    if "active" in attributes and "active" not in excluded_attributes or all_attributes:
        if (is_active := nc_user.get("enabled", None)) is not None:
            scim_user["active"] = is_active

    if "emails" in attributes and "emails" not in excluded_attributes or all_attributes:
        scim_user["emails"] = [
            Email.model_validate(
                {"value": nc_user["email"], "type": "other", "primary": True}
            )
        ]

    if "name" in attributes and "name" not in excluded_attributes or all_attributes:
        scim_user["name"] = Name.model_validate({"formatted": nc_user["displayname"]})

    if (
        "displayName" in attributes
        and "displayName" not in excluded_attributes
        or all_attributes
    ):
        scim_user["displayName"] = nc_user["displayname"]

    return User.model_validate(scim_user)


def user_scim_to_nc(scim_user: User) -> dict[str, Any]:
    # Editable fields
    # displayname
    # email
    # phone
    # address
    # website
    # twitter
    nc_user = {
        # "enabled": scim_user.active,
        "user_id": scim_user.user_name,
        "display_name": scim_user.display_name,
        "email": e[0].value if (e := scim_user.emails) else None,
    }
    return nc_user


def group_nc_to_scim(
    nc_group_id: str,
    attributes: list[str] = [],
    excluded_attributes: list[str] = [],
) -> Group:
    all_attributes = not attributes  # if no attributes are passed
    scim_group = {}

    scim_group["id"] = nc_group_id

    if (
        "displayName" in attributes
        and "displayName" not in excluded_attributes
        or all_attributes
    ):
        scim_group["displayName"] = nc_group_id

    # Members are not included by default, as doing so requires making a request to Nextcloud for every individual group's members, significantly increasing the request time.
    # Also, SCIM is typically implemented this way.
    if "members" in attributes and "members" not in excluded_attributes:
        members, _ = GroupAPI.get_members(nc_group_id)
        if members is None:
            scim_group["members"] = []
        elif isinstance(members, str):
            scim_group["groups"] = [GroupMember.model_validate({"value": members})]
        elif isinstance(members, list):
            scim_group["members"] = [
                GroupMember.model_validate({"value": m}) for m in members
            ]

    return Group.model_validate(scim_group)


if __name__ == "__main__":
    import json

    # from pathlib import Path
    # with open(Path('.').resolve() / 'sample' / 'users.json', 'r') as f:
    #     sample_data: dict[str, list[dict[str, Any]]] = json.load(f)
    # nc_users = sample_data['users']
    # scim_users: list[User] = []
    # for u in nc_users:
    #     scim_users.append(user_nc_to_scim(u))
    # for u in scim_users:
    #     print(json.dumps(u.model_dump(), indent=2))
    #     print(json.dumps(user_scim_to_nc(u), indent=2), end='\n\n')
    print(
        json.dumps(
            group_nc_to_scim("App Admins", attributes=["displayName"]).model_dump(),
            indent=2,
        )
    )
