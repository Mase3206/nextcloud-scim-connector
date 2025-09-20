#!/usr/bin/env bash

set -e

nc_url="localhost:8080"
secret="admin"

declare -a groups=(names haters numbers)

declare -a group_names=(alice bob jane john)
declare -a group_haters=(john user1)
declare -a group_numbers=(user1 user2 user3 user4 user5 user6)



# Create the groups
for g in "${groups[@]}"; do
    echo -n "Creating '$g' group... "
    curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/groups \
        -d groupid="$g" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | grep \<status\> | sed -Ee 's/(\>|\<)/ /g' | awk '{ print $2 }'
done
unset g



# Add users to "names" group
for u in "${group_names[@]}"; do
    echo -n "Adding '$u' user to 'names' group... "
    curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="names" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | grep \<status\> | sed -Ee 's/(\>|\<)/ /g' | awk '{ print $2 }'
done
unset u

# Add users to "haters" group
for u in "${group_haters[@]}"; do
    echo -n "Adding '$u' user to 'haters' group... "
    curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="haters" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | grep \<status\> | sed -Ee 's/(\>|\<)/ /g' | awk '{ print $2 }'
done
unset u

# Add users to "numbers" group
for u in "${group_numbers[@]}"; do
    echo -n "Adding '$u' user to 'numbers' group... "
    curl -X POST http://admin:$secret@$nc_url/ocs/v1.php/cloud/users/$u/groups \
        -d groupid="numbers" \
        -H "OCS-APIRequest: true" 2> /dev/null \
        | grep \<status\> | sed -Ee 's/(\>|\<)/ /g' | awk '{ print $2 }'
done
unset u

unset nc_url secret groups group_names group_haters group_numbers
