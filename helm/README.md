# Application Helm Chart

This Helm chart deploys an application with Deployment, Service, Horizontal Pod Autoscaler (HPA), ConfigMap, Secret, and Ingress resources.

## Features

- **Deployment** with configurable replicas, resources, and probes
- **Service** for internal cluster communication
- **Horizontal Pod Autoscaler (HPA)** with CPU and custom metrics (RPS) support
- **ConfigMap** for non-sensitive configuration
- **Secret** for sensitive data (API keys, credentials)
- **Ingress** for external access
- **Resource limits**: 500m CPU / 1Gi memory requests, 1000m CPU / 1Gi memory limits
- **Health probes**: Liveness and readiness probes configured
- **Environment variables**: Configurable VECTOR_BACKEND, MODEL_NAME, and provider keys

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- kubectl configured to access your cluster
- Metrics Server installed (for HPA CPU metrics)
- Custom Metrics API adapter (e.g., Prometheus Adapter) for RPS-based autoscaling

## Installation

### Basic Installation

```bash
# Install the chart with default values
helm install my-app ./helm

# Install with a custom release name
helm install my-release ./helm

# Install into a specific namespace
helm install my-app ./helm --namespace my-namespace --create-namespace
```

### Installation with Custom Values

```bash
# Install with custom values file
helm install my-app ./helm -f my-values.yaml

# Install with inline value overrides
helm install my-app ./helm \
  --set env.VECTOR_BACKEND=qdrant \
  --set env.MODEL_NAME=gpt-4 \
  --set image.repository=my-registry/my-app \
  --set image.tag=v1.0.0
```

### Installation with Secret Values

```bash
# Set provider API key via --set (will be base64 encoded automatically)
helm install my-app ./helm \
  --set secret.data.PROVIDER_API_KEY="your-api-key-here"

# Or use --set-file for reading from a file
echo -n "your-api-key-here" > /tmp/api-key.txt
helm install my-app ./helm \
  --set-file secret.data.PROVIDER_API_KEY=/tmp/api-key.txt
```

## Configuration

### Key Configuration Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas (ignored if autoscaling enabled) | `2` |
| `image.repository` | Container image repository | `nginx` |
| `image.tag` | Container image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `80` |
| `service.targetPort` | Container port | `8080` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `1000m` |
| `resources.limits.memory` | Memory limit | `1Gi` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `60` |
| `autoscaling.targetRPS` | Target requests per second | `100` |
| `env.VECTOR_BACKEND` | Vector backend type | `pinecone` |
| `env.MODEL_NAME` | Model name | `text-embedding-ada-002` |
| `ingress.enabled` | Enable ingress | `false` |

### Environment Variables

The chart supports the following environment variables:

- `VECTOR_BACKEND`: Vector database backend (e.g., `pinecone`, `qdrant`, `weaviate`, `chroma`)
- `MODEL_NAME`: ML model name (e.g., `text-embedding-ada-002`, `gpt-4`)
- `PROVIDER_API_KEY`: Provider API key (stored in Secret)

### Example values.yaml

```yaml
replicaCount: 3

image:
  repository: my-registry/my-app
  tag: v1.0.0
  pullPolicy: Always

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

resources:
  limits:
    cpu: 1000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 60
  targetRPS: 100
  customMetrics:
    enabled: true
    metricName: "http_requests_per_second"
    targetValue: "100"

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5

env:
  VECTOR_BACKEND: "qdrant"
  MODEL_NAME: "gpt-4"
  PROVIDER_API_KEY: ""

configMap:
  enabled: true
  data:
    LOG_LEVEL: "info"
    API_TIMEOUT: "30"

secret:
  enabled: true
  data:
    PROVIDER_API_KEY: ""  # Set via --set or external secrets

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: app.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: app-tls
      hosts:
        - app.example.com
```

## Common Operations

### Upgrade

```bash
# Upgrade with new values
helm upgrade my-app ./helm -f my-values.yaml

# Upgrade with inline values
helm upgrade my-app ./helm \
  --set env.VECTOR_BACKEND=weaviate \
  --set image.tag=v1.1.0
```

### Rollback

```bash
# List release history
helm history my-app

# Rollback to previous version
helm rollback my-app

# Rollback to specific revision
helm rollback my-app 2
```

### Uninstall

```bash
# Uninstall the release
helm uninstall my-app

# Uninstall from specific namespace
helm uninstall my-app --namespace my-namespace
```

### View Status

```bash
# Check release status
helm status my-app

# List all releases
helm list

# List releases in specific namespace
helm list --namespace my-namespace
```

## Using kubectl Commands

### Deploy with kubectl

```bash
# Render templates and apply
helm template my-app ./helm | kubectl apply -f -

# Render with custom values
helm template my-app ./helm -f my-values.yaml | kubectl apply -f -

# Apply to specific namespace
helm template my-app ./helm | kubectl apply -n my-namespace -f -
```

### View Resources

```bash
# View all resources
kubectl get all -l app.kubernetes.io/instance=my-app

# View deployment
kubectl get deployment my-app

# View pods
kubectl get pods -l app.kubernetes.io/instance=my-app

# View service
kubectl get service my-app

# View HPA
kubectl get hpa my-app

# View configmap
kubectl get configmap my-app-configmap

# View secret
kubectl get secret my-app-secret
```

### Check Pod Logs

```bash
# View logs for all pods
kubectl logs -l app.kubernetes.io/instance=my-app --tail=100

# View logs for specific pod
kubectl logs <pod-name>

# Follow logs
kubectl logs -f -l app.kubernetes.io/instance=my-app
```

### Describe Resources

```bash
# Describe deployment
kubectl describe deployment my-app

# Describe pod
kubectl describe pod <pod-name>

# Describe service
kubectl describe service my-app

# Describe HPA
kubectl describe hpa my-app
```

### Debugging

```bash
# Execute command in pod
kubectl exec -it <pod-name> -- /bin/sh

# Port forward to local machine
kubectl port-forward service/my-app 8080:80

# View events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check pod status
kubectl get pods -l app.kubernetes.io/instance=my-app -o wide
```

## HPA Configuration

### CPU-Based Autoscaling

The HPA is configured to scale based on CPU utilization (default: 60%). Ensure Metrics Server is installed:

```bash
# Check if metrics-server is running
kubectl get deployment metrics-server -n kube-system

# If not installed, install metrics-server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Custom Metrics (RPS) Autoscaling

For RPS-based autoscaling, you need a custom metrics adapter. Example with Prometheus Adapter:

1. Install Prometheus and Prometheus Adapter
2. Configure the adapter to expose `http_requests_per_second` metric
3. Ensure the metric name matches `autoscaling.customMetrics.metricName` in values.yaml

Verify custom metrics:

```bash
# Check available custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | jq

# Check specific metric
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/default/pods/*/http_requests_per_second"
```

## Health Probes

The chart configures both liveness and readiness probes:

- **Liveness Probe**: Checks `/health` endpoint every 10 seconds
- **Readiness Probe**: Checks `/ready` endpoint every 5 seconds

Ensure your application implements these endpoints:

- `GET /health` - Should return 200 OK when the application is healthy
- `GET /ready` - Should return 200 OK when the application is ready to serve traffic

## Security Best Practices

1. **Secrets Management**: Never commit secrets to version control. Use:
   - `--set` flags for one-time deployments
   - External secrets management (e.g., Sealed Secrets, External Secrets Operator)
   - Kubernetes secrets created separately

2. **Image Pull Secrets**: If using private registries:

```yaml
imagePullSecrets:
  - name: my-registry-secret
```

3. **Service Account**: The chart creates a service account. Configure RBAC as needed.

4. **Network Policies**: Consider adding NetworkPolicy resources for network isolation.

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>

# Check if image pull is successful
kubectl get events --field-selector involvedObject.name=<pod-name>
```

### HPA Not Scaling

```bash
# Check HPA status
kubectl describe hpa my-app

# Verify metrics are available
kubectl top pods

# Check custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1"
```

### Service Not Accessible

```bash
# Verify service endpoints
kubectl get endpoints my-app

# Check service selector matches pod labels
kubectl get pods --show-labels
kubectl get service my-app -o yaml
```

### Ingress Issues

```bash
# Check ingress status
kubectl describe ingress my-app

# Verify ingress controller is running
kubectl get pods -n ingress-nginx  # or your ingress namespace

# Check ingress events
kubectl get events --field-selector involvedObject.name=my-app
```

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Custom Metrics API](https://github.com/kubernetes-sigs/custom-metrics-apiserver)
