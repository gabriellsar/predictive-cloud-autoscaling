#!/usr/bin/env bash
# Baixa apenas machine_usage (~1,7 GB compactado) do Alibaba Cluster Trace 2018.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
cd data/raw
# -C - retoma o download se cair; --retry tenta de novo em erro de rede
curl -L -C - --retry 10 --retry-delay 5 --retry-all-errors -o machine_usage.tar.gz \
  http://aliopentrace.oss-cn-beijing.aliyuncs.com/v2018Traces/machine_usage.tar.gz
( sha256sum machine_usage.tar.gz 2>/dev/null || shasum -a 256 machine_usage.tar.gz ) \
  | tee machine_usage.tar.gz.sha256
echo "Extraindo..."
tar -xzf machine_usage.tar.gz
ls -lh
