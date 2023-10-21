docker ps -f "name=cropbot" --format "{{.ID}}" | xargs docker kill
docker build . -t cropbot
docker run --name="cropbot" -v $PWD:/home -d cropbot
docker logs -f cropbot
