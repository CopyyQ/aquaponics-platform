#!/usr/bin/env bash
set -euo pipefail

gateway_url="${PUBLIC_MONITORING_GATEWAY_URL:-http://127.0.0.1:8088}"
runtime_dir="${PUBLIC_MONITORING_RUNTIME_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/runtime/public-monitoring}"
runtime_file="${runtime_dir}/tunnel.json"

write_status() {
  local status="$1"
  local url="${2:-}"
  local temporary_file="${runtime_file}.tmp"
  mkdir -p "${runtime_dir}"
  printf '{"status":"%s","url":"%s","gateway_url":"%s"}\n' "${status}" "${url}" "${gateway_url}" > "${temporary_file}"
  mv "${temporary_file}" "${runtime_file}"
}

command -v cloudflared >/dev/null 2>&1 || {
  write_status "unavailable"
  echo "cloudflared chưa được cài đặt hoặc không có trong PATH." >&2
  echo "Hãy cài cloudflared từ tài liệu chính thức của Cloudflare rồi chạy lại script." >&2
  exit 1
}

cloudflared --version
curl --fail --silent --show-error --max-time 10 "${gateway_url}/" >/dev/null || {
  write_status "gateway-unavailable"
  echo "Public Monitoring Gateway chưa hoạt động tại ${gateway_url}." >&2
  echo "Chạy: docker compose up -d public-monitoring-gateway" >&2
  exit 1
}

write_status "starting"
trap 'write_status "stopped"' EXIT INT TERM

echo "Đang tạo Cloudflare Quick Tunnel tới ${gateway_url}..."
cloudflared tunnel --no-autoupdate --url "${gateway_url}" 2>&1 | while IFS= read -r line; do
  printf '%s\n' "${line}"
  if [[ "${line}" =~ (https://[a-zA-Z0-9-]+\.trycloudflare\.com) ]]; then
    tunnel_url="${BASH_REMATCH[1]}"
    write_status "running" "${tunnel_url}"
    echo "Remote Monitoring URL: ${tunnel_url}"
  fi
done
