# Nextcloud SCIM Connector

SCIM connector for Nextcloud

Essentially a translator from SCIM to Nextcloud's horribly janky official APIs:
- for users: https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html
- for groups: https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#create-a-group

## To-Do

- [x] Add user to group
- [x] Remove user from group
- [ ] Update user attribute — [PATCH /Users](https://scim.dev/playground/users.html#update-attribute)
- [ ] Handle multiple patch operations at once
    - [ ] PATCH /Users
    - [ ] PATCH /Groups
- [ ] HTTP Bearer authentication — [potentially helpful StackOverflow thread](https://stackoverflow.com/questions/76867554/fastapi-how-to-access-bearer-token)
- [ ] Set user backend in Nextcloud when creating users
    - [ ] Verify that the backend can even be set via the NC API
    - [ ] Custom SCIM likely required for this
        - Creating the custom attribute: [Guide for Entra ID](https://developers.staffbase.com/guides/customattributes-scim/#creating-custom-attributes-in-microsoft-entra-id)
    - [ ] Property mappings in Authentik or other IdP
        - Potential issue with Authentik: [goauthentik/authentik#14202](https://github.com/goauthentik/authentik/issues/14202)
- [ ] Testing!! — in progress
    - [ ] pytest — in use, need more test cases
    - [x] Nextcloud test environment — uses a customized container based on [ghcr.io/juliusknorr/nextcloud-dev-php81](ghcr.io/juliusknorr/nextcloud-dev-php81:latest)
    - [x] GitHub Action


## Development

[nektos/act](https://github.com/nektos/act) is required for automated unit tests. It runs the GitHub Actions locally, which spin up and provision an isolated and consistent test environment.

These are the expected groups. They are configured automatically by [tests/prep-users-and-groups.sh](./tests/prep-users-and-groups.sh) using offical APIs.

![Group members](assets/group-membership.png)
