define _env_config
cat <<-EOF
	# Default dev config -- not for production use!
	SCIM_TOKEN="$(pwgen 64 1)"

	NEXTCLOUD_BASEURL="localhost:8080"
	NEXTCLOUD_HTTPS=0
	NEXTCLOUD_USERNAME="admin"
	NEXTCLOUD_SECRET="admin"
EOF
endef
export env_config = $(value _env_config)

-include .env

env:
	@echo "Configuring your local environment for development usage."
	@eval "$$env_config" > .env

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

build:
	yes | docker builder prune --all
	poetry build --clean
	docker build -t nc-scim .

lint:
	poetry run ruff check --fix

format:
	poetry run ruff format