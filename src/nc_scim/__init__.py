from typing import Any

import yaml

with open("config.yml") as f:
    raw_config: dict[str, Any] = yaml.safe_load(f)

SCIM_TOKEN = str(raw_config.get("scim", {}).get("token"))


_nc = raw_config.get("nextcloud", {})
NEXTCLOUD_BASEURL = f"{_nc.get('baseurl')}/ocs/v1.php/cloud"
NEXTCLOUD_HTTPS = True if _nc.get("https", True) else False
NEXTCLOUD_USERNAME: str = _nc.get("username")
NEXTCLOUD_SECRET: str = _nc.get("secret")

# print(SCIM_TOKEN, NEXTCLOUD_BASEURL)
