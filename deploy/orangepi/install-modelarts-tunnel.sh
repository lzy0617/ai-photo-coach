#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "用法: sudo $0 <SSH域名> <SSH端口> <香橙派PEM绝对路径> [SSH用户]" >&2
  echo "示例: sudo $0 authoring-ssh-modelarts-xxxxx.huawei.com 31092 /root/.ssh/modelarts.pem ma-user" >&2
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage
  exit 2
fi

if [[ ${EUID} -ne 0 ]]; then
  echo "错误：请使用 root 或 sudo 执行。" >&2
  exit 1
fi

ssh_host=$1
ssh_port=$2
ssh_key=$3
ssh_user=${4:-ma-user}

if [[ ! ${ssh_host} =~ ^[A-Za-z0-9.-]+$ ]]; then
  echo "错误：SSH 域名格式不正确。" >&2
  exit 1
fi

if [[ ! ${ssh_port} =~ ^[0-9]+$ ]] || (( ssh_port < 1 || ssh_port > 65535 )); then
  echo "错误：SSH 端口必须是 1 到 65535 之间的数字。" >&2
  exit 1
fi

if [[ ! ${ssh_user} =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "错误：SSH 用户名格式不正确。" >&2
  exit 1
fi

if [[ ${ssh_key} != /* || ! -f ${ssh_key} ]]; then
  echo "错误：找不到 PEM 私钥，必须传入香橙派上的绝对路径：${ssh_key}" >&2
  exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
service_source="${script_dir}/photo-ai-modelarts-tunnel.service"

if [[ ! -f ${service_source} ]]; then
  echo "错误：安装脚本旁边缺少 photo-ai-modelarts-tunnel.service。" >&2
  exit 1
fi

install -d -m 700 /root/.ssh
chmod 600 "${ssh_key}"

echo "正在验证香橙派能否登录 ModelArts……"
/usr/bin/ssh \
  -i "${ssh_key}" \
  -p "${ssh_port}" \
  -o BatchMode=yes \
  -o ConnectTimeout=15 \
  -o StrictHostKeyChecking=accept-new \
  "${ssh_user}@${ssh_host}" \
  true

install -d -m 755 /etc/photo-ai
{
  printf 'MODELARTS_SSH_HOST=%s\n' "${ssh_host}"
  printf 'MODELARTS_SSH_PORT=%s\n' "${ssh_port}"
  printf 'MODELARTS_SSH_USER=%s\n' "${ssh_user}"
  printf 'MODELARTS_SSH_KEY=%s\n' "${ssh_key}"
} > /etc/photo-ai/modelarts-tunnel.env
chmod 600 /etc/photo-ai/modelarts-tunnel.env

install -m 644 "${service_source}" /etc/systemd/system/photo-ai-modelarts-tunnel.service
systemctl daemon-reload
systemctl enable --now photo-ai-modelarts-tunnel.service

echo
echo "SSH 隧道服务已安装。状态："
systemctl --no-pager --full status photo-ai-modelarts-tunnel.service || true
echo
echo "接下来验证：curl http://127.0.0.1:18000/health"
