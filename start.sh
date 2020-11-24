git pull
docker stop unburnt_container_on_server
docker rm unburnt_container_on_server
docker build -t unburnt_container_on_server .
docker run -d --name unburnt_container_on_server -p 8080:8080 --restart=always unburnt_container_on_server
