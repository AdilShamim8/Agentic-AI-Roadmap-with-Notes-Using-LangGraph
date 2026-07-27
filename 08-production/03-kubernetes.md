# Kubernetes

Module: 08-production
Chapter: 03-kubernetes
Status: beta
Last reviewed: 2026-07-27
Estimated time: 2 hours

## Learning objectives

- Deploy a LangGraph agent to Kubernetes
- Configure horizontal pod autoscaling based on request rate
- Use a StatefulSet for Postgres checkpointing (or use a managed Postgres)
- Reason about when Kubernetes is justified vs. Docker Compose

## Prerequisites

- [02 Docker deployment](02-docker-deployment.md)

## Conceptual foundation

Kubernetes is the production deployment target for teams that need horizontal scaling, multi-region deployment, or integration with an existing Kubernetes-based infrastructure. For most teams, Docker Compose on a single VM is sufficient up to a few hundred requests per minute. Kubernetes becomes justified when:

- Traffic exceeds what a single VM can handle (typically, 500+ requests per minute sustained).
- You need multi-region deployment for latency or availability.
- Your organization already runs Kubernetes and has the operational expertise.
- You need to run multiple agents with different resource requirements on shared infrastructure.

The Kubernetes deployment has four components:

1. Deployment. Runs the LangGraph server pods. Configured with horizontal pod autoscaling (HPA) based on CPU or custom metrics (request rate).
2. StatefulSet or managed Postgres. For checkpointing. Use a StatefulSet for self-hosted Postgres, or a managed Postgres (AWS RDS, Cloud SQL) for production.
3. Service. Exposes the LangGraph server internally (ClusterIP) and externally (LoadBalancer or Ingress).
4. ConfigMap and Secret. Hold the configuration (langgraph.json) and secrets (API keys).

The HPA scales the number of LangGraph pods based on load. The scaling metric should be request rate (or queue depth), not CPU - LLM calls are I/O-bound, so CPU stays low even when the agent is busy. Define a custom metric in Prometheus and use it as the HPA target.

## Worked example

A minimal Kubernetes manifest for a LangGraph deployment. Full manifests in [`08-production/k8s/`](k8s/).

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: langgraph-agent
  template:
    metadata:
      labels:
        app: langgraph-agent
    spec:
      containers:
      - name: langgraph
        image: my-registry/langgraph-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: openai-api-key
        - name: POSTGRES_URL
          value: postgresql://postgres:$(POSTGRES_PASSWORD)@postgres:5432/langgraph
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: langgraph-agent
spec:
  type: LoadBalancer
  selector:
    app: langgraph-agent
  ports:
  - port: 80
    targetPort: 8000
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: langgraph-agent
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: langgraph-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "10"
```

## Evaluation

No eval. The test is: the agent responds correctly when accessed through the Kubernetes Service, and the HPA scales up under load.

## Production notes

In production, the two biggest concerns are Postgres (use a managed instance, not a StatefulSet, for any non-trivial deployment) and observability (use Prometheus + Grafana in addition to LangSmith). The third concern is graceful shutdown: when a pod is terminating, in-flight requests should complete before the pod is killed. Configure `terminationGracePeriodSeconds` and implement a readiness probe so the load balancer stops sending traffic to the terminating pod.

## Common pitfalls

- Using CPU as the HPA metric. Why: it is the default. Fix: use request rate; LLM calls are I/O-bound.
- Self-hosting Postgres on Kubernetes for production. Why: it works in dev. Fix: use a managed Postgres for production.
- Not configuring graceful shutdown. Why: it works in dev. Fix: set `terminationGracePeriodSeconds` and implement a readiness probe.

## Further reading

- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [LangGraph self-hosted](https://langchain-ai.github.io/langgraph/cloud/deployment/self_hosted/)

## Checklist

- [ ] Write a Kubernetes Deployment manifest for a LangGraph agent
- [ ] Configure an HPA based on request rate
- [ ] Use a managed Postgres for production checkpointing
- [ ] Configure graceful shutdown and readiness probes
