# from typing import Any

# import yaml

# with open("config.yml") as f:
#     raw_config: dict[str, Any] = yaml.safe_load(f)

from pathlib import Path

from environs import env

env.read_env()
CONNECTOR_BASEPATH: str = str(
    (env.path("CONNECTOR_BASEPATH", Path("/")) / "scim" / "v2").resolve()
)
SCIM_TOKEN: str = env.str("SCIM_TOKEN")
NEXTCLOUD_BASEURL: str = f"{env.str('NEXTCLOUD_BASEURL')}/ocs/v1.php/cloud"
NEXTCLOUD_HTTPS: bool = env.bool("NEXTCLOUD_HTTPS")
NEXTCLOUD_USERNAME: str = env.str("NEXTCLOUD_USERNAME")
NEXTCLOUD_SECRET: str = env.str("NEXTCLOUD_SECRET")

# SCIM_TOKEN = str(raw_config.get("scim", {}).get("token"))


# _nc = raw_config.get("nextcloud", {})
# NEXTCLOUD_BASEURL = f"{_nc.get('baseurl')}/ocs/v1.php/cloud"
# NEXTCLOUD_HTTPS = True if _nc.get("https", True) else False
# NEXTCLOUD_USERNAME: str = _nc.get("username")
# NEXTCLOUD_SECRET: str = _nc.get("secret")

# print(SCIM_TOKEN, NEXTCLOUD_BASEURL)
