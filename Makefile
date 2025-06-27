start:
	docker compose up -d
stop:
	docker compose down

reload:
	docker-compose down -v
	docker-compose build --no-cache
	docker-compose up -d

build-data:
	docker exec -it postgres psql -U trainuser -d traindb -f /docker-entrypoint-initdb.d/backup_server_logement_20_06.sql

spark-immo:
	docker compose run spark-job logic-immo

spark-test:
	docker compose run spark-job test
spark-comment:
	docker compose run spark-job comment