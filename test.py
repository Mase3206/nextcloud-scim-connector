import json

import requests

data = json.loads("""{
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "name": {"formatted": "Test User 2"},
    "active": true,
    "emails": [{"value": "testuser2@example.com"}],
    "userName": "testuser2"
}""")

print(data)
print()

print(
    requests.post(
        url="http://localhost:8000/Users",
        data=json.dumps(data),
        headers={"Content-Type": "application/scim+json"},
    ).text
)
