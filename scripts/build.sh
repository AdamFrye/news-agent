docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t thebiggestfrye/news-agent:latest \
  --push .
