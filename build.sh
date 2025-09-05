docker-compose -f docker-compose.yml build

docker tag pingouinfinihub/hyperv-monitor pingouinfinihub/hyperv-monitor:latest
docker push pingouinfinihub/hyperv-monitor:latest