#!/usr/bin/env bash

set -e

nc_url="localhost:8080"
secret="admin"

declare -a groups=(names haters numbers)

declare -a group_names=(alice bob jane john)
declare -a group_haters=(john user1)
declare -a group_numbers=(user1 user2 user3 user4 user5 user6)

declare -a all_users=(alice bob jane john user1 user2 user3 user4 user5 user6)


# Create the groups
for g in "${groups[@]}"; do
    echo -n "Creating '$g' group... "
    apistat=$(curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/groups \
        -d groupid="$g" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | xq -e '//ocs/meta/status')
    echo $apistat
done
unset g



# Add users to "names" group
for u in "${group_names[@]}"; do
    echo -n "Adding '$u' user to 'names' group... "
    apistat=$(curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="names" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | xq -e '//ocs/meta/status')
    echo $apistat
done
unset u

# Add users to "haters" group
for u in "${group_haters[@]}"; do
    echo -n "Adding '$u' user to 'haters' group... "
    apistat=$(curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="haters" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | xq -e '//ocs/meta/status')
    echo $apistat
done
unset u

# Add users to "numbers" group
for u in "${group_numbers[@]}"; do
    echo -n "Adding '$u' user to 'numbers' group... "
    apistat=$(curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="numbers" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | xq -e '//ocs/meta/status')
    echo $apistat
done
unset u



# Assign an email to each user
for u in "${all_users[@]}"; do
    new_email="$u@example.com"
    echo -n "Setting $u's email to '$new_email'... "
    apistat=$(curl -X PUT http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u \
        -d key="email" -d value="$new_email" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | xq -e '//ocs/meta/status')
    # echo $apistat

    retrieved_email=$(curl http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u -H "OCS-APIRequest: true" 2> /dev/null | xq -e '//ocs/data/email')

    if [[ "$retrieved_email" != "$new_email" ]]; then
        echo "Retrieved email ($retrieved_email) does not match what was set ($new_email)"
        exit 1
    else
        echo $apistat
    fi
done
unset u

unset nc_url secret groups group_names group_haters group_numbers all_users