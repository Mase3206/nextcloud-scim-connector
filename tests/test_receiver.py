import pytest
import requests
from fastapi.testclient import TestClient
from scim2_models import (Bulk, ChangePassword, ETag, Filter, Group,
                          ListResponse, Patch, PatchOp, ServiceProviderConfig,
                          Sort, User)

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

    response = client.get('/Users?attributes=groups')
    assert response.status_code == 200
    raw_data = response.json()
    users = ListResponse[User].model_validate(raw_data).model_dump()
    assert users == expected








###########################################
# ┌─────────────────────────────────────┐ #
# │    G R O U P   E N D P O I N T S    │ #
# └─────────────────────────────────────┘ #
###########################################
