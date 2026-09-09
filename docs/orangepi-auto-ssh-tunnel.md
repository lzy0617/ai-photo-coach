# 香橙派自动连接 ModelArts VLM

本文将香橙派到华为云 ModelArts 的 SSH 本地端口转发安装为 `systemd` 服务。安装完成后，系统开机会自动连接；网络短暂中断或 SSH 进程退出后，会每隔 5 秒重试。

最终转发关系：

```text
香橙派 127.0.0.1:18000
          │ SSH Tunnel
          ▼
ModelArts 127.0.0.1:8000
```

该服务只在香橙派回环地址监听 `18000`，不会把 VLM 接口直接暴露到局域网。

## 1. 安装前准备

需要从 ModelArts 控制台确认：

- SSH 域名，例如 `authoring-ssh-modelarts-xxxxx.huawei.com`；
- SSH 外部端口，例如 `31092`；
- SSH 用户，通常是 `ma-user`；
- 与该 Notebook 匹配的 PEM 私钥。

同时保证 ModelArts 中的 VLM API 已启动并监听：

```text
127.0.0.1:8000
```

如果 PEM 还在 Mac 上，先在香橙派创建目录：

```sh
mkdir -p /root/.ssh
chmod 700 /root/.ssh
```

再从 Mac 上传；把 `/Mac上的实际路径/modelarts.pem` 换成真实路径：

```sh
scp /Mac上的实际路径/modelarts.pem root@10.151.161.60:/root/.ssh/modelarts.pem
```

回到香橙派设置权限：

```sh
chmod 600 /root/.ssh/modelarts.pem
```

私钥不要放进 `/var/www`，也不要提交进 Git。

## 2. 把安装文件放到香橙派

需要把仓库中的以下两个文件放在香橙派的同一个目录：

```text
deploy/orangepi/install-modelarts-tunnel.sh
deploy/orangepi/photo-ai-modelarts-tunnel.service
```

如果新版仓库已经同步到 `/root/photo-ai`，执行：

```sh
cd /root/photo-ai/deploy/orangepi
chmod +x install-modelarts-tunnel.sh
```

也可以在 Mac 仓库根目录直接上传：

```sh
scp deploy/orangepi/install-modelarts-tunnel.sh \
    deploy/orangepi/photo-ai-modelarts-tunnel.service \
    root@10.151.161.60:/root/
```

这种情况下，后续脚本路径是 `/root/install-modelarts-tunnel.sh`。

## 3. 安装并启动自动隧道

在香橙派执行以下命令，并替换三个示例参数：

```sh
cd /root/photo-ai/deploy/orangepi

./install-modelarts-tunnel.sh \
  authoring-ssh-modelarts-xxxxx.huawei.com \
  31092 \
  /root/.ssh/modelarts.pem \
  ma-user
```

参数依次是：

1. ModelArts SSH 域名；
2. ModelArts SSH 外部端口；
3. PEM 在香橙派上的绝对路径；
4. SSH 用户，可省略，默认 `ma-user`。

脚本会先进行一次无交互 SSH 登录验证。验证通过后，它会：

- 创建 `/etc/photo-ai/modelarts-tunnel.env`；
- 安装 `photo-ai-modelarts-tunnel.service`；
- 设置开机启动；
- 立即启动隧道。

如果私钥设置了口令，`systemd` 无法在开机时交互输入，需使用适合该 Notebook 的无口令专用密钥。

## 4. 验证

查看服务：

```sh
systemctl status photo-ai-modelarts-tunnel --no-pager
```

确认本地端口：

```sh
ss -lntp | grep 18000
```

正常应监听：

```text
127.0.0.1:18000
```

验证完整隧道：

```sh
curl http://127.0.0.1:18000/health
```

预期返回类似：

```json
{"status":"ok","model":"Qwen3-VL-8B-Instruct","device":"npu:0"}
```

最后从手机网页触发一次“AI 深度分析”。

## 5. 常用管理命令

```sh
# 查看状态
systemctl status photo-ai-modelarts-tunnel --no-pager

# 查看最近日志
journalctl -u photo-ai-modelarts-tunnel -n 100 --no-pager

# 实时查看日志
journalctl -u photo-ai-modelarts-tunnel -f

# 重启
systemctl restart photo-ai-modelarts-tunnel

# 停止
systemctl stop photo-ai-modelarts-tunnel

# 禁止开机启动
systemctl disable photo-ai-modelarts-tunnel
```

修改连接参数时，编辑：

```sh
vim /etc/photo-ai/modelarts-tunnel.env
```

随后重启：

```sh
systemctl restart photo-ai-modelarts-tunnel
```

## 6. 故障判断

### 服务不断重启

查看日志：

```sh
journalctl -u photo-ai-modelarts-tunnel -n 100 --no-pager
```

常见原因包括 SSH 域名或端口错误、PEM 不匹配、Notebook 已停止、香橙派暂时无法连接互联网。

### `18000` 已被占用

```sh
ss -lntp | grep 18000
```

先确认是不是之前手动运行的 SSH Tunnel。停止旧的手动 Tunnel 后再重启服务：

```sh
systemctl restart photo-ai-modelarts-tunnel
```

### 隧道运行但 `/health` 失败

如果 SSH 服务显示 `active (running)`，但下面命令失败：

```sh
curl http://127.0.0.1:18000/health
```

通常说明云端 VLM API 没有运行，或者没有监听 `127.0.0.1:8000`。此时需要进入 ModelArts 检查云端 `uvicorn`，不是重新配置 Nginx。

## 7. 边缘后端地址

香橙派后端应继续使用：

```text
VLM_API_URL=http://127.0.0.1:18000/analyze
```

Nginx、手机和前端都不需要知道 ModelArts SSH 地址。
