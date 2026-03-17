docker-compose -f docker-compose.yml build

docker tag pingouinfinihub/hyperv-monitor pingouinfinihub/hyperv-monitor:2.1.0
docker push pingouinfinihub/hyperv-monitor:2.1.0