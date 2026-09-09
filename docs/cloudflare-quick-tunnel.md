# Cloudflare 临时域名访问流程

本文使用 Cloudflare Quick Tunnel，为香橙派上的 AI Photo Coach 临时生成一个公网 HTTPS 地址，例如：

```text
https://random-words.trycloudflare.com
```

这种方式不要求购买域名、修改 DNS 或创建 Cloudflare Tunnel Token，适合临时演示和手机摄像头测试。它不适合作为长期部署方案。

## 1. 访问链路

```text
手机或电脑浏览器
        │ 随机 trycloudflare.com HTTPS 地址
        ▼
Cloudflare Quick Tunnel
        │
        ▼
香橙派 cloudflared
        │ http://127.0.0.1:80
        ▼
Nginx
  ├── /      → 前端静态网页
  └── /api/* → YOLO/FastAPI :8000
                      │
                      └── SSH Tunnel :18000 → ModelArts Qwen3-VL
```

Quick Tunnel 应连接 Nginx 的 `80` 端口，而不是直接连接 FastAPI 的 `8000` 端口。只有经过 Nginx，网页和 `/api/*` 才能通过同一个 HTTPS 地址正常工作。

## 2. 启动前检查

在香橙派执行：

```sh
systemctl is-active nginx
systemctl is-active photo-ai
systemctl is-active photo-ai-modelarts-tunnel
```

正常情况下三条命令都返回：

```text
active
```

检查网页入口：

```sh
curl -I http://127.0.0.1/
```

预期返回：

```text
HTTP/1.1 200 OK
```

检查香橙派后端：

```sh
curl http://127.0.0.1:8000/health
```

需要 AI 深度分析时，再检查云端转发：

```sh
curl http://127.0.0.1:18000/health
```

只有网页入口返回 `200 OK` 后，才继续启动 Quick Tunnel。

## 3. 安装 cloudflared

先确认是否已经安装：

```sh
cloudflared --version
```

如果显示版本号，跳到下一节。

香橙派通常是 ARM64，可先确认：

```sh
dpkg --print-architecture
```

预期输出：

```text
arm64
```

下载对应的 `.deb`：

```sh
curl --location \
  --output /tmp/cloudflared.deb \
  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$(dpkg --print-architecture).deb"
```

安装并检查：

```sh
dpkg -i /tmp/cloudflared.deb
cloudflared --version
```

Cloudflare 提供 Linux ARM64 的二进制和 `.deb` 安装包，详见 [cloudflared 下载文档](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)。

## 4. 启动临时 HTTPS 地址

在香橙派执行：

```sh
cloudflared tunnel --url http://127.0.0.1:80
```

不要写成：

```sh
cloudflared tunnel --url http://127.0.0.1:8000
```

`8000` 只有后端 API，没有前端静态网页，并且会绕过 Nginx。

启动成功后，终端会输出类似：

```text
Your quick Tunnel has been created!
https://random-words.trycloudflare.com
```

实际随机地址以当次终端输出为准。复制其中完整的 `https://...trycloudflare.com` 地址。

这条命令会一直占用当前终端；保持该终端和进程运行，临时地址才能继续访问。

## 5. 手机验收

为了确认请求确实经过公网 Tunnel，可以暂时关闭手机 Wi-Fi，使用移动网络打开生成的 HTTPS 地址。

按顺序测试：

1. 网页正常加载；
2. 从相册选择照片；
3. YOLO 人物框和快速建议正常；
4. 点击“AI 深度分析”；
5. Qwen3-VL 返回场景、光线和摄影建议；
6. 点击实时拍摄；
7. 允许浏览器使用摄像头；
8. 确认画面、拍照和分析正常。

Quick Tunnel 提供 HTTPS，因此满足浏览器摄像头 API 的安全上下文要求。用户仍需在浏览器中授予摄像头权限。

## 6. 停止和重新启动

在运行 `cloudflared` 的终端按：

```text
Control+C
```

临时 Tunnel 会立即停止，之前的随机地址也将失效。

再次运行：

```sh
cloudflared tunnel --url http://127.0.0.1:80
```

Cloudflare 通常会生成一个新的随机地址，因此每次重新启动后都要重新复制和分享 URL。

Quick Tunnel 默认不是 systemd 服务，也不会开机自动恢复。临时演示结束后不需要执行卸载操作。

## 7. 安全注意事项

Quick Tunnel 地址是公网地址，随机 URL 不等于身份认证。拿到地址的人可以访问网页并调用 `/api/*`。

使用时应注意：

- 只在测试或演示期间运行；
- 不在公开群组、代码仓库或截图中长期暴露地址；
- 演示结束后按 `Control+C` 停止；
- 不通过网页上传隐私照片；
- 观察香橙派和云端 NPU 使用情况；
- 不将 FastAPI 的 `8000` 端口作为 Quick Tunnel origin；
- 需要长期开放时改用正式 Tunnel，并添加 Cloudflare Access 或应用身份验证。

Cloudflare 官方将 Quick Tunnel 定位为开发和测试功能，不保证 SLA 或持续可用性。[Quick Tunnel 官方说明](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)

## 8. 常见问题

### `cloudflared: command not found`

说明尚未安装，按照第 3 节安装 ARM64 `.deb`。

### Quick Tunnel 与 `config.yml` 冲突

Cloudflare 当前说明：如果 `.cloudflared` 目录中存在 `config.yaml`，Quick Tunnel 可能无法启动。

先检查：

```sh
find /root/.cloudflared -maxdepth 1 \
  \( -name 'config.yml' -o -name 'config.yaml' \) \
  -print 2>/dev/null
```

如果确实存在正式 Tunnel 配置，不要删除。临时改名，例如：

```sh
mv /root/.cloudflared/config.yml /root/.cloudflared/config.yml.disabled-for-quick-tunnel
```

Quick Tunnel 使用结束后恢复：

```sh
mv /root/.cloudflared/config.yml.disabled-for-quick-tunnel /root/.cloudflared/config.yml
```

实际文件名如果是 `config.yaml`，命令中的文件名也要对应修改。

### 页面显示 `502 Bad Gateway`

先检查 Nginx：

```sh
systemctl status nginx --no-pager
curl -I http://127.0.0.1/
```

如果本地请求失败，先修复 Nginx；如果本地返回 `200`，查看当前 cloudflared 终端输出。

### Quick Tunnel 无法连接 Cloudflare

查看终端错误。Cloudflare Tunnel 需要香橙派能够向外访问 `7844` 端口，并可使用 UDP/QUIC 或 TCP/HTTP2。

新版 `cloudflared` 可以运行诊断：

```sh
cloudflared tunnel diag
```

参考 [Cloudflare Tunnel 连接检查](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/troubleshoot-tunnels/connectivity-prechecks/)。

### 网页能打开，但 YOLO 请求失败

```sh
systemctl status photo-ai --no-pager
curl http://127.0.0.1:8000/health
```

同时确认 Quick Tunnel 的 origin 是：

```text
http://127.0.0.1:80
```

### YOLO 正常，但 AI 深度分析失败

```sh
systemctl status photo-ai-modelarts-tunnel --no-pager
curl http://127.0.0.1:18000/health
```

如果 SSH Tunnel 正常但健康检查失败，检查 ModelArts 上的 Qwen API。

### 深度分析返回 `524`

Cloudflare 当前默认 Proxy Read Timeout 约为 125 秒。如果 Qwen3-VL 在这段时间内没有返回响应，Cloudflare 可能返回 `524`。

优先压缩上传图片并将深度分析控制在 120 秒以内。长期方案应把深度分析改成异步任务提交与结果轮询。参考 [Cloudflare 524 说明](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-524/)。

### 返回 `429`

Quick Tunnel 当前最多允许约 200 个并发中的请求。它不适合高并发或正式服务。

## 9. 最短使用流程

每次临时演示前，在香橙派执行：

```sh
systemctl is-active nginx
systemctl is-active photo-ai
systemctl is-active photo-ai-modelarts-tunnel
curl -I http://127.0.0.1/
curl http://127.0.0.1:18000/health
cloudflared tunnel --url http://127.0.0.1:80
```

复制终端生成的 HTTPS 地址，用手机访问。演示完成后按 `Control+C` 停止 Quick Tunnel。
