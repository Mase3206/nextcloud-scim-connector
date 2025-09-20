#!/usr/bin/env bash

host='nextcloud:80'

[[ "$(curl -I http://$host -o /dev/null -w %{http_code} 2> /dev/null)" == "302" ]]
