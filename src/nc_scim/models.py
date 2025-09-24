from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ByteSize, ConfigDict, EmailStr, Field
from pydantic_extra_types.phone_numbers import PhoneNumber
from scim2_models import Address, Email, GroupMembership, Name
from scim2_models import PhoneNumber as ScimPhoneNumber
from scim2_models import User as ScimUser


class NCUser(BaseModel):
    id: str = Field(alias="userid")
    """Also accepts `userid` as a valid field alias."""
    email: EmailStr
    displayname: str
    # password: str = Field('This is not set by SCIM.', frozen=True)
    enabled: bool = False
    groups: list[str] = []
    # subadmin: Optional[list[str]] = None
    quota: Optional[ByteSize] = None
    # language: Optional[LanguageAlpha2] = None
    phone: Optional[PhoneNumber] = None
    address: Optional[str] = None

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    def to_scim(self):
        scim_user = {
            "userName": self.id,
            "id": self.id,
            "displayName": self.displayname,
            "name": Name.model_validate({"formatted": self.displayname}),
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
            ],
            "addresses": [Address.model_validate({"formatted": self.address})],
            "phoneNumbers": [ScimPhoneNumber.model_validate({"value": self.phone})],
        }

        return ScimUser.model_validate(scim_user)

    @classmethod
    def from_scim(cls, scim_user: ScimUser) -> NCUser:
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
                {"value": "testuser2@example.com", "type": "other", "primary": True}
            ],
            "groups": [],
        }
    )
    NCUser.from_scim(scim_user)
    return


if __name__ == "__main__":
    _tc()
