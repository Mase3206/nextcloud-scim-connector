# Nextcloud SCIM Connector

SCIM connector for [Nextcloud](https://nextcloud.com/)

This is essentially a translator from [SCIM](https://scim.cloud/) to Nextcloud's user and group provisioning APIs (see [# Extra Notes](#extra-notes) for links). This project aims to add SCIM service provider (the application-end) functionality to Nextcloud, as the existing Nextcloud [scimserviceprovider project](https://forge.libre.sh/libre.sh/scimserviceprovider) has had very little development recently, and I'm tired of waiting for it to finish.

I aim to make this implementation as complete as is reasonably possible for a full-time student (me) to implement in their free time, but I am sure I have left some things out. It's specifically optimized for [Authentik](https://goauthentik.io) and [user_oidc](https://github.com/nextcloud/user_oidc), as that is my intended deployment, but it'll likely work with other IdPs and SSO protocols and implementations.

Some things are deliberately left unimplemented, as I do not have the capacity at this time to implement them well. See the next three sections for details on what this does and does not implement, and what I plan on implementing in the future.

> [!NOTE]
> This connector currently provisions users into the default built-in user database, not ones specific to user_oidc and the like. If user_oidc is configured correctly though, it can still take over authentication of these users. I may consider reworking this to target the user_oidc endpoints instead in the future.

## What's missing or not implemented

- PATCH operations on users — see note under To-Do's
- the /Me endpoint
- Sorting
- ETags
- Bulk operations
- Password changing &mdash; this will never be implemented, as you should probably rely on an external authentication provider when using SCIM.
- Filter

## What *is* implemented

Generally speaking, everything not listed above *should* be implemented, but there are a few things that should be explicitly pointed out to ensure clarity:

- PATCH operations on groups — required for updating group membership
- GET /ServiceProviderConfig — ensures the identity provider knows what this does and doesn't support, like filter operations.

## Future to-do's

- [ ] Target the right user backend (oidc_user, etc.) instead of the default built-in one
    - Will require a modified API wrapper for those specific endpoints
- [ ] Testing!! — in progress
    - [ ] pytest
        - [x] Receiver
        - [ ] NCUser to/from ScimUser conversion
        - [ ] NCApi calls, both UserAPI and GroupAPI

> [!NOTE]
> See issues for more to-dos. The ones here in this list are essentially in the backlog of my backlog.


## Development

### System dependencies for development

- Python 3.13+
- Poetry
- `xq`, command-line XML formatter and querier &mdash; used in a handful of places
    - Get it: [github.com/sibprogrammer/xq](https://github.com/sibprogrammer/xq)
- `jq`, JSON formatter and querier &mdash; not required, but highly recommended if you use cURL for testing
- Docker and Docker Compose
- `act`, local GitHub Action runner &mdash; used for the full test case runner
    - Get it: [github.com/nektos/act](https://github.com/nektos/act)
- GNU Make

### Developing in this environment

This project makes extensive use of GNU Make for common and lengthy commands and multi-step actions. All formulae are in the [Makefile](./Makefile) in the project's root.

Set up your local development environment:
```shell
# Install dependencies
poetry install --all-groups
# Create .env file with default values for development
make env
```

Running the dev server:
```shell
make dev
```

Testing:
```shell
# Start the Nextcloud dev environment
make test-up

# Run PyTest
poetry run pytest

# Stop the Nextcloud dev environment
make test-down

# Run the GitHub PyTest action
make test
```

Building the nc-scim Docker image:
```shell
make build
```


Linting and formatting:
```shell
make lint
make format
```

> [!IMPORTANT]
> Ruff is used for linting and formatting. Please use them before submitting any code. Code that does not conform to the formatting rules configured in the pyproject.toml file will not be accepted.

### Extra notes

[nektos/act](https://github.com/nektos/act) is required for automated unit tests. It runs the GitHub Actions locally, which spin up and provision an isolated and consistent test environment.

These are the expected groups. They are configured automatically by [tests/prep-users-and-groups.sh](./tests/prep-users-and-groups.sh) using offical APIs.
Also, the [command-line tool `xq`](https://github.com/sibprogrammer/xq) is used in the prep-users-and-groups.sh script to parse the XML.

![Group members](assets/group-membership.png)

- Nextcloud user API: https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_users.html
- Nextcloud group API: https://docs.nextcloud.com/server/latest/admin_manual/configuration_user/instruction_set_for_groups.html#create-a-group
