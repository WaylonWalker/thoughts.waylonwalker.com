default: build tag push set-image
fresh: create-ns cred convert deploy viz
update: convert patch

build:
    podman build -t registry.wayl.one/thoughts -f Dockerfile .
tag:
    podman tag registry.wayl.one/thoughts registry.wayl.one/thoughts:$(git rev-parse --short HEAD)
push:
    podman push registry.wayl.one/thoughts registry.wayl.one/thoughts:$(git rev-parse --short HEAD)
    podman push registry.wayl.one/thoughts registry.wayl.one/thoughts:latest
set-image:
    kubectl set image deployment/thoughts --namespace thoughts thoughts=registry.wayl.one/thoughts:$(git rev-parse --short HEAD)

create-ns:
    kubectl create ns thoughts && echo created ns thoughts || echo namespace thoughts already exists
cred:
    kubectl get secret regcred --output=yaml -o yaml | sed 's/namespace: default/namespace: thoughts/' | kubectl apply -n thoughts -f - && echo deployed secret || echo secret exists
convert:
    kompose convert -o deployment.yaml -n thoughts --replicas 3
deploy:
    kubectl apply -f deployment.yaml
delete:
    kubectl delete all --all -n thoughts --timeout=0s
viz:
    k8sviz -n thoughts --kubeconfig $KUBECONFIG -t png -o thoughts-k8s.png
restart:
    kubectl rollout restart -n thoughts deployment/thoughts
patch:
    kubectl patch -f deployment.yaml

describe:
    kubectl get deployment -n thoughts
    kubectl get rs -n thoughts
    kubectl get pod -n thoughts
    kubectl get svc -n thoughts
    kubectl get ing -n thoughts


describe-pod:
    kubectl describe pod -n thoughts

logs:
    kubectl logs --all-containers -l io.kompose.service=thoughts -n thoughts -f
