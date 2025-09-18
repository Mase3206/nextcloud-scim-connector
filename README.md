# nextcloud-scim-connector
SCIM connector for Nextcloud

## To-Do

- [x] Add user to group
- [x] Remove user from group
- [ ] Update user attribute — [PATCH /Users](https://scim.dev/playground/users.html#update-attribute)
- [ ] HTTP Bearer authentication — [potentially helpful StackOverflow thread](https://stackoverflow.com/questions/76867554/fastapi-how-to-access-bearer-token)
- [ ] Set user backend in Nextcloud when creating users
    - [ ] Verify that the backend can even be set via the NC API
    - [ ] Custom SCIM likely required for this
        - Creating the custom attribute: [Guide for Entra ID](https://developers.staffbase.com/guides/customattributes-scim/#creating-custom-attributes-in-microsoft-entra-id)
    - [ ] Property mappings in Authentik or other IdP
        - Potential issue with Authentik: [goauthentik/authentik#14202](https://github.com/goauthentik/authentik/issues/14202)
