from fastapi import FastAPI, logger
from nc_scim.forwarder import UserAPI, GroupAPI
# from nc_scim.models import User
import json
from typing import Optional

app = FastAPI()

@app.get('/Schemas')
def get_schemas(): ...

@app.get('/Users')
def get_all_users():
    all_users, _ = UserAPI.get_all()
    logger.logger.debug(all_users)

    scim_users: list = []
    for u in all_users:
        u_data, _ = UserAPI.get(u)
        scim_users.append(u_data)
    
    return scim_users
    # _payload = {
    #     "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
    #     "totalResults": len(all_users),
    #     "Resources": [
    #         {
    #             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    #             "id": "2441309d85324e7793ae",
    #             "externalId": "7fce0092-d52e-4f76-b727-3955bd72c939",
    #             "meta": {
    #                 "resourceType": "User",
    #                 "created": "2018-03-27T19:59:26.000Z",
    #                 "lastModified": "2018-03-27T19:59:26.000Z"
                    
    #             },
    #             "userName": "Test_User_00aa00aa-bb11-cc22-dd33-44ee44ee44ee",
    #             "name": {
    #                 "familyName": "familyName",
    #                 "givenName": "givenName"
    #             },
    #             "active": True,
    #             "emails": [
    #                     {
    #                     "value": "Test_User_11bb11bb-cc22-dd33-ee44-55ff55ff55ff@testuser.com",
    #                     "type": "work",
    #                     "primary": True
    #                 }
    #             ]
    #         }
    #     ],
    #     "startIndex": 1,
    #     "itemsPerPage": 20
    # }
