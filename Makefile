
at_server: at_server.py at_requirements.txt at_config.ini at_dockerfile
	docker build -f at_dockerfile -t at_server:latest ./
	docker save -o at_server at_server:latest

wt_server: wt_server.py wt_requirements.txt	wt_config.ini wt_dockerfile
	docker build -f wt_dockerfile -t wt_server:latest ./
	docker save -o wt_server wt_server:latest

run_wt: wt_server
	docker rm -f wt_server 2> /dev/null || true
	docker run -d -p 80:5000  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} -e AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} --name wt_server wt_server:latest

run_at: at_server
	docker rm -f at_server 2> /dev/null || true
	docker run -d  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
    -e AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} --restart always --name at_server at_server:latest

clean_containers:
	@echo "Warning: This will delete all docker containers"
	@read -p "Are you sure? [y/N] " ans && ans=$${ans:-N} ; \
    if [ $${ans} = y ] || [ $${ans} = Y ]; then \
        docker rm `docker ps -aq` ; \
    else \
        printf "Aborted" ; \
    fi
	

clean_images:
	@echo "Warning: This will delete all images"
	@read -p "Are you sure? [y/N] " ans && ans=$${ans:-N} ; \
    if [ $${ans} = y ] || [ $${ans} = Y ]; then \
        docker rmi `docker image ls --format "{{ .ID }}"`; \
    else \
        printf "Aborted" ; \
    fi
	


clean:
	rm -rf at_server wt_server at wt

.PHONY: clean clean_containers clean_images run_wt run_at

