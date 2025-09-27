from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
)
from pydantic_extra_types.phone_numbers import PhoneNumber
from scim2_models import (
    Address,
    Email,
    Group as ScimGroup,
    GroupMember,
    GroupMembership,
    Name,
    PhoneNumber as ScimPhoneNumber,
    User as ScimUser,
)


class Quota(BaseModel):
    free: int
    used: int
    total: int
    relative: int
    quota: int

    @classmethod
    def model_validate(cls, *args, **kwargs):
        cls = super().model_validate(*args, **kwargs)
        if cls.quota > 0:
            if cls.total == cls.free + cls.used:
                raise ValidationError(
                    "User has quota set, but the given free and used amounts do not add up to the given total."
                )

        return cls


def coerce_to_list(elements: list | Any | None) -> list:
    """Used by Pydantic to coerce a lone string to a single-element list containing that string, or a `None` to an empty list."""
    if not elements:
        return []
    elif isinstance(elements, list):
        return elements
    else:
        return [elements]


class NCUser(BaseModel):
    id: str = Field(alias="userid")
    """Also accepts `userid` as a valid field alias."""
    email: Optional[EmailStr] = None
    displayname: str
    # password: str = Field('This is not set by SCIM.', frozen=True)
    enabled: bool = False
    groups: Annotated[list[str], BeforeValidator(coerce_to_list)] = []
    # subadmin: Optional[list[str]] = None
    quota: Optional[Quota] = None
    """User quota as used by Nextcloud. Optional."""
    # language: Optional[LanguageAlpha2] = None
    phone: Optional[PhoneNumber] = None
    address: Optional[str] = None

    model_config = ConfigDict(
        validate_by_alias=True, validate_by_name=True, extra="allow"
    )

    def to_scim(self) -> ScimUser:
        scim_user = {
            "userName": self.id,
            "id": self.id,
            "displayName": self.displayname,
            "name": Name.model_validate({"formatted": self.displayname}),
            "active": self.enabled,
            "groups": [
                GroupMembership(
                    display=g,
                    type="direct",
                    value=g,
                    ref=None,
                )
                for g in self.groups
            ],
            "emails": [
                Email.model_validate(
                    {
                        "value": self.email,
                        "type": "other",
                        "primary": True,
                    }
                )
            ]
            if self.email
            else [],
            "addresses": [Address.model_validate({"formatted": self.address})]
            if self.address
            else [],
            "phoneNumbers": [ScimPhoneNumber.model_validate({"value": self.phone})]
            if self.phone
            else [],
        }

        return ScimUser.model_validate(scim_user)

    @staticmethod
    def from_scim(scim_user: ScimUser) -> NCUser:
        # These fields are required.
        assert scim_user.user_name
        assert scim_user.display_name
        assert (e := scim_user.emails) and e[0].value

        # Get or parse address
        if (addrs := scim_user.addresses) and len(addrs) > 0:
            if (addr := addrs[0]).formatted:
                address = addr.formatted
            elif (
                addr.street_address
                and addr.locality
                and addr.region
                and addr.postal_code
                and addr.country
            ):
                # Using American formatting here
                address = f"{addr.street_address}, {addr.locality}, {addr.region} {addr.postal_code}, {addr.country}"
            else:
                address = None
        else:
            address = None

        nc_user = {
            "id": scim_user.user_name,
            "displayname": scim_user.display_name,
            "email": scim_user.emails[0].value,
            "groups": [g.value for g in scim_user.groups] if scim_user.groups else [],
            "phone": scim_user.phone_numbers[0].value
            if (scim_user.phone_numbers and len(scim_user.phone_numbers) > 0)
            else None,
            "address": address,
        }

        return NCUser.model_validate(nc_user)


class NCGroup(BaseModel):
    groupid: str
    members: Annotated[list[str], BeforeValidator(coerce_to_list)] = []

    def to_scim(self) -> ScimGroup:
        data = {
            "id": self.groupid,
            "displayName": self.groupid,
            "members": [
                GroupMember.model_validate({"value": gm}) for gm in self.members
            ],
        }

        return ScimGroup.model_validate(data)

    @staticmethod
    def from_scim(scim_group: ScimGroup) -> NCGroup:
        group_members = (
            [g.value for g in scim_group.members] if scim_group.members else []
        )

        return NCGroup.model_validate(
            {"groupid": scim_group.id, "members": group_members}
        )


def _tc():
    d: dict[str, Any] = {
        "userid": "wow",
        "email": "wow@example.com",
        "displayname": "wow dude",
    }
    u = NCUser.model_validate(d)

    scim_user = ScimUser.model_validate(
        {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": "testuser2",
            "userName": "testuser2",
            "name": {"formatted": "Test User 2"},
            "displayName": "Test User 2",
            "active": True,
            "emails": [
                {
                    "value": "testuser2@example.com",
                    "type": "other",
                    "primary": True,
                }
            ],
            "groups": [],
        }
    )
    NCUser.from_scim(scim_user)
    return


if __name__ == "__main__":
    _tc()
