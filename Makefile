test-up:
	docker compose --file tests/nextcloud-docker-dev/docker-compose.yml up -d nextcloud

test-run:
	-poetry run pytest

test-down:
	docker compose --file tests/nextcloud-docker-dev/docker-compose.yml down

test:
	$(MAKE) test-up
	sleep 10
	-poetry run pytest
	$(MAKE) test-down
