import json

import requests

add_group_data = json.loads("""{
  "schemas": [
    "urn:ietf:params:scim:api:messages:2.0:PatchOp"
  ],
  "Operations": [
    {
      "op": "add",
      "path": "members",
      "value": [
        {"value": "testuser2"},
        {"value": "araycove"}
      ]
    }
  ]
}""")


new_user_data = json.loads("""{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "name": {"formatted": "Test User 2"},
    "active": true,
    "emails": [{"value": "testuser2@example.com"}],
    "userName": "testuser2"
}""")
# print(json.dumps(new_user_data, indent=2))

# print(data)
# print()

print(
    requests.post(
        url="http://localhost:8000/Users",
        data=json.dumps(new_user_data),
        headers={"Content-Type": "application/scim+json"},
    ).text
)

print(
    requests.patch(
        url="http://localhost:8000/Groups/Test Group",
        data=json.dumps(add_group_data),
        headers={"Content-Type": "application/scim+json"},
    ).text
)
