import json

import pytest
from fastapi.testclient import TestClient
from scim2_models import (
    Group,
    ListResponse,
    User,
)

from nc_scim.receiver import app

client = TestClient(app)


#########################################
# ┌───────────────────────────────────┐ #
# │    U S E R   E N D P O I N T S    │ #
# └───────────────────────────────────┘ #
#########################################


def test_get_all_users_no_groups():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'], 'Resources': [{'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'admin', 'userName': 'admin'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'alice', 'userName': 'alice'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'bob', 'userName': 'bob'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'jane', 'userName': 'jane'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'john', 'userName': 'john'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'localhost', 'userName': 'localhost'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user1', 'userName': 'user1'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user2', 'userName': 'user2'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user3', 'userName': 'user3'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user4', 'userName': 'user4'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user5', 'userName': 'user5'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user6', 'userName': 'user6'}]}
    # fmt: on

    response = client.get("/Users")
    assert response.status_code == 200
    raw_data = response.json()
    users = ListResponse[User].model_validate(raw_data).model_dump()
    assert users == expected


def test_get_all_users_with_groups():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'], 'Resources': [{'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'admin', 'userName': 'admin', 'groups': [{'value': 'admin', 'display': 'admin', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'alice', 'userName': 'alice', 'groups': [{'value': 'names', 'display': 'names', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'bob', 'userName': 'bob', 'groups': [{'value': 'names', 'display': 'names', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'jane', 'userName': 'jane', 'groups': [{'value': 'names', 'display': 'names', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'john', 'userName': 'john', 'groups': [{'value': 'haters', 'display': 'haters', 'type': 'direct'}, {'value': 'names', 'display': 'names', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'localhost', 'userName': 'localhost', 'groups': []}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user1', 'userName': 'user1', 'groups': [{'value': 'haters', 'display': 'haters', 'type': 'direct'}, {'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user2', 'userName': 'user2', 'groups': [{'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user3', 'userName': 'user3', 'groups': [{'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user4', 'userName': 'user4', 'groups': [{'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user5', 'userName': 'user5', 'groups': [{'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'user6', 'userName': 'user6', 'groups': [{'value': 'numbers', 'display': 'numbers', 'type': 'direct'}]}]}
    # fmt: on

    response = client.get("/Users?attributes=groups")
    assert response.status_code == 200
    raw_data = response.json()
    users = ListResponse[User].model_validate(raw_data).model_dump()
    assert users == expected


@pytest.mark.dependency()
def test_create_user():
    # fmt: off
    new_user_data = {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'name': {'formatted': 'Test User 2'}, 'active': True, 'emails': [{'value': 'testuser2@example.com'}], 'userName': 'testuser2', 'displayName': 'Test User 2'}
    expected_user_data = {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'testuser2', 'userName': 'testuser2', 'name': {'formatted': 'Test User 2'}, 'displayName': 'Test User 2', 'active': True, 'emails': [{'value': 'testuser2@example.com', 'type': 'other', 'primary': True}], 'groups': []}
    # fmt: on

    response = client.post(
        "/Users",
        json=new_user_data,
        headers={"Content-Type": "application/scim+json"},
    )
    assert response.status_code == 201, "Status code is not '201 Created'"
    assert response.text == "", "Response text is not empty"

    response = client.get("/Users/testuser2")
    assert response.status_code == 200, "Status code is not '200 OK'"
    assert json.loads(response.text) == expected_user_data, (
        "User data post-creation does not match what was expected"
    )


@pytest.mark.dependency(depends=["test_create_user"])
def test_get_user():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'], 'id': 'testuser2', 'userName': 'testuser2', 'name': {'formatted': 'Test User 2'}, 'displayName': 'Test User 2', 'active': True, 'emails': [{'value': 'testuser2@example.com', 'type': 'other', 'primary': True}], 'groups': []}
    # fmt: on
    response = client.get("/Users/testuser2")
    assert response.status_code == 200
    user = User.model_validate(response.json()).model_dump()
    assert user == expected


@pytest.mark.dependency(depends=["test_get_user"])
def test_delete_user():
    response = client.delete("/Users/testuser2")
    assert response.status_code == 204, "Status code is not '204 No Content'"
    assert response.text == "", "Response text is not empty"

    response = client.get("/Users/testuser2")
    assert response.status_code == 404, (
        "Status code is not '404 Not Found', meaning the user still exists in Nextcloud"
    )


###########################################
# ┌─────────────────────────────────────┐ #
# │    G R O U P   E N D P O I N T S    │ #
# └─────────────────────────────────────┘ #
###########################################


def test_get_all_groups():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'], 'Resources': [{'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'admin', 'displayName': 'admin'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'haters', 'displayName': 'haters'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'names', 'displayName': 'names'}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'numbers', 'displayName': 'numbers'}]}
    # fmt: on

    response = client.get("/Groups")
    assert response.status_code == 200

    groups = ListResponse[Group].model_validate(response.json()).model_dump()
    assert groups == expected


def test_get_all_groups_with_members():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:api:messages:2.0:ListResponse'], 'Resources': [{'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'admin', 'members': [{'value': 'admin'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'haters', 'members': [{'value': 'john'}, {'value': 'user1'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'names', 'members': [{'value': 'alice'}, {'value': 'bob'}, {'value': 'jane'}, {'value': 'john'}]}, {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'numbers', 'members': [{'value': 'user1'}, {'value': 'user2'}, {'value': 'user3'}, {'value': 'user4'}, {'value': 'user5'}, {'value': 'user6'}]}]}
    # fmt: on

    response = client.get("/Groups?attributes=members")
    assert response.status_code == 200

    groups = ListResponse[Group].model_validate(response.json()).model_dump()
    assert groups == expected


def test_get_group_by_id():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'haters', 'displayName': 'haters', 'members': [{'value': 'john'}, {'value': 'user1'}]}
    # fmt: on

    response = client.get("/Groups/haters")
    assert response.status_code == 200

    group = Group.model_validate(response.json()).model_dump()
    assert group == expected


@pytest.mark.dependency()
def test_create_group():
    # fmt: off
    expected = {'schemas': ['urn:ietf:params:scim:schemas:core:2.0:Group'], 'id': 'test2', 'displayName': 'test2', 'members': []}
    # fmt: on

    response = client.post("/Groups", json={"displayName": "test2"})
    assert response.status_code == 201

    group = Group.model_validate(response.json()).model_dump()
    assert group == expected


@pytest.mark.dependency(depends=["test_create_group"])
def test_delete_group():
    response = client.delete("/Groups/test2")
    assert response.status_code == 204

    response = client.get("/Groups/test2")
    assert response.status_code == 404
