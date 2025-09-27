TEST_SECRET="admin"

test-build:
	docker compose -f tests/docker-compose.yml build nextcloud

test-up:
	docker compose -f tests/docker-compose.yml up --force-recreate -d --wait
	@echo "Sleeping an additional 10 seconds to allow the users to be created"
	sleep 10
	./tests/prep-users-and-groups.sh

test-down:
	docker compose -f tests/docker-compose.yml down -v

test:
	$(MAKE) test-down
	act -j pytest

dev:
	poetry run fastapi dev src/nc_scim/receiver.py