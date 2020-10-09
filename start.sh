git pull
docker stop unburnt_container_on_server
docker rm unburntimageonserver
docker build -t unburntimageonserver .
docker run -d --name unburnt_container_on_server -p 8080:8080 --restart=always unburntimageonserver
