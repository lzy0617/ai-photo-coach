# 通过香橙派 IP 访问网页

本文说明如何把 AI Photo Coach 前端部署到香橙派，并让同一局域网内的手机或电脑通过香橙派 IP 访问。当前实际示例 IP 是 `10.151.161.60`；如果路由器重新分配地址，应以香橙派当时显示的 IP 为准。

## 1. 访问链路

```text
手机或电脑浏览器
        │ http://香橙派IP/
        ▼
香橙派 Nginx :80
        ├── /          → /var/www/photo-ai 前端静态文件
        └── /api/*     → 127.0.0.1:8000 YOLO/FastAPI
                              │
                              └── 127.0.0.1:18000 → ModelArts VLM
```

正式静态网页由 Nginx 提供，不再依赖 Mac 上的 `npm run dev`。浏览器请求 `/api/*` 时，由 Nginx 转发给香橙派本机后端，因此前端和 API 使用同一个 IP，不需要额外配置 CORS 地址。

## 2. 前置条件

香橙派应具备：

- `/root/photo-ai/frontend/dist/index.html` 和 `assets/`；
- 正在运行的 `photo-ai.service`；
- 正在运行的 `nginx.service`；
- 需要 AI 深度分析时，运行 `photo-ai-modelarts-tunnel.service`；
- 手机或电脑与香橙派处于可互相访问的局域网。

查看服务：

```sh
systemctl is-active nginx
systemctl is-active photo-ai
systemctl is-active photo-ai-modelarts-tunnel
```

正常情况下三条命令都返回：

```text
active
```

## 3. 确认香橙派 IP

在香橙派执行：

```sh
ip -br addr
```

或者：

```sh
hostname -I
```

当前设备示例：

```text
wlan0  UP  10.151.161.60/24
```

因此网页地址是：

```text
http://10.151.161.60/
```

不要把 URL 写成 Markdown 链接，也不要在 `http` 前后添加方括号、圆括号或反斜杠。

## 4. 首次部署前端

### 4.1 在 Mac 构建

进入前端目录：

```sh
cd "/Users/reiayanami/Documents/Note/huaweicloud/ai-photo-coach/frontend"
```

安装依赖并构建：

```sh
npm ci
npm run build
```

构建产物位于：

```text
frontend/dist/
```

生产部署中不使用 Vite 的 `API_PROXY_TARGET`；浏览器直接请求同源 `/api/*`，代理工作由 Nginx 完成。

### 4.2 上传到香橙派

在 Mac 的 `frontend` 目录执行：

```sh
scp -r dist root@10.151.161.60:/root/photo-ai/frontend/
```

上传后，在香橙派确认：

```sh
ls -lah /root/photo-ai/frontend/dist
```

应至少看到：

```text
index.html
assets
```

### 4.3 复制到 Nginx 静态目录

不要让 Nginx 直接读取 `/root`。将构建产物复制到 `/var/www`：

```sh
mkdir -p /var/www/photo-ai
cp -a /root/photo-ai/frontend/dist/. /var/www/photo-ai/
chown -R www-data:www-data /var/www/photo-ai
find /var/www/photo-ai -type d -exec chmod 755 {} \;
find /var/www/photo-ai -type f -exec chmod 644 {} \;
```

确认部署结果：

```sh
ls -lah /var/www/photo-ai
```

## 5. 配置 Nginx

编辑：

```sh
vim /etc/nginx/sites-available/photo-ai
```

配置内容：

```nginx
server {
    listen 80;
    server_name _;

    root /var/www/photo-ai;
    index index.html;

    client_max_body_size 20M;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 10s;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
    }
}
```

首次启用站点：

```sh
ln -s /etc/nginx/sites-available/photo-ai /etc/nginx/sites-enabled/photo-ai
```

如果链接已经存在，不需要重复执行。默认站点仍存在时可以先确认目标：

```sh
ls -l /etc/nginx/sites-enabled
```

确认后移除默认站点链接：

```sh
rm /etc/nginx/sites-enabled/default
```

检查并加载配置：

```sh
nginx -t
systemctl reload nginx
systemctl enable nginx
```

`nginx -t` 必须显示配置语法正确后才能重新加载。

## 6. 在香橙派上逐层验收

### 6.1 前端入口

```sh
curl -I http://127.0.0.1/
```

预期：

```text
HTTP/1.1 200 OK
```

### 6.2 YOLO/FastAPI 后端

```sh
curl http://127.0.0.1:8000/health
```

应返回香橙派、Ascend 和 YOLO 模型信息。

### 6.3 Nginx API 代理

先确认前端使用的同源健康检查已经经过 80 端口：

```sh
curl http://127.0.0.1/health
```

它应返回 JSON，而不是 `index.html`。然后使用测试照片验证快速分析：

```sh
curl -X POST http://127.0.0.1/api/analyze-fast \
  -F 'image=@/root/photo-ai/test.jpg;type=image/jpeg'
```

实际分析接口通过以下路径转发：

```text
/api/analyze-fast
/api/deep-analyze
```

### 6.4 云端深度分析链路

```sh
curl http://127.0.0.1:18000/health
```

应返回 Qwen3-VL 的模型和 NPU 信息。

## 7. 从手机或电脑访问

1. 确认访问设备与香橙派处于同一个可互通网络；
2. 在浏览器地址栏完整输入 `http://香橙派IP/`；
3. 当前设备示例是 `http://10.151.161.60/`；
4. 先选择一张照片，确认 YOLO 分析；
5. 再触发 AI 深度分析，确认 Qwen3-VL 返回结果。

从另一台电脑也可以先用命令验证：

```sh
curl -I http://10.151.161.60/
```

如果命令返回 `200 OK`，但某个浏览器仍无法访问，通常是该浏览器或电脑的代理、VPN、扩展规则问题，不应继续修改香橙派 Nginx。

## 8. 手机摄像头与 HTTPS

通过相册选择照片通常可以在普通 HTTP 页面使用。但是浏览器的实时摄像头 API 属于安全能力，除 `localhost` 外通常要求可信 HTTPS。

因此：

- `http://10.151.161.60/` 适合先验证网页、选图、YOLO 和深度分析；
- 如果手机无法授权实时摄像头，应配置 HTTPS；
- 不要为了绕过摄像头限制而关闭浏览器安全策略；
- 后续可以使用域名与可信证书，将入口改成 `https://你的域名/`。

## 9. 更新前端

前端代码修改后，不需要重新配置 Nginx。重复以下流程即可。

Mac：

```sh
cd "/Users/reiayanami/Documents/Note/huaweicloud/ai-photo-coach/frontend"
npm run build
scp -r dist root@10.151.161.60:/root/photo-ai/frontend/
```

香橙派：

```sh
cp -a /root/photo-ai/frontend/dist/. /var/www/photo-ai/
chown -R www-data:www-data /var/www/photo-ai
```

静态文件更新不需要重启 FastAPI。通常也不需要重启 Nginx；浏览器强制刷新页面即可。如果修改的是 Nginx 配置，才需要：

```sh
nginx -t
systemctl reload nginx
```

## 10. 固定 IP

`10.151.161.60` 可能是 DHCP 动态地址。IP 改变后，旧网页地址就会失效。

推荐在路由器或热点管理页面中，为香橙派 `wlan0` 的 MAC 地址配置 DHCP 地址保留。查看 MAC 地址：

```sh
ip link show wlan0
```

这种方式比直接修改香橙派网络配置更不容易造成设备失联。固定后，将最终地址记录为项目访问入口。

## 11. 常见故障

### 浏览器显示 `ERR_ADDRESS_UNREACHABLE`

请求尚未到达 Nginx。依次检查：

```sh
# 香橙派
ip -br addr
ss -lntp | grep ':80 '

# 访问设备
ping 10.151.161.60
nc -vz 10.151.161.60 80
```

如果其他手机能访问，只有某台电脑失败，优先检查该电脑的 VPN 或代理，并将香橙派 IP 或 `10.0.0.0/8` 设置为直连。

### Nginx 返回 `500 Internal Server Error`

查看：

```sh
tail -n 50 /var/log/nginx/error.log
```

常见原因是 Nginx 被配置为读取 `/root/photo-ai/frontend/dist`，或者 `/var/www/photo-ai/index.html` 不存在。确认：

```sh
ls -lah /var/www/photo-ai/index.html
```

并保证 Nginx 使用：

```nginx
root /var/www/photo-ai;
```

### Nginx 返回 `502 Bad Gateway`

网页入口正常，但香橙派后端没有响应。检查：

```sh
systemctl status photo-ai --no-pager
curl http://127.0.0.1:8000/health
journalctl -u photo-ai -n 100 --no-pager
```

### 网页能打开，但 AI 深度分析失败

先确认 YOLO 后端，再检查 SSH Tunnel：

```sh
curl http://127.0.0.1:8000/health
systemctl status photo-ai-modelarts-tunnel --no-pager
curl http://127.0.0.1:18000/health
```

如果 Tunnel 是 `active (running)`，但 `18000/health` 失败，通常是云端 Qwen API 没有启动。

### 防火墙阻止 80 端口

```sh
ufw status
```

如果 UFW 已启用：

```sh
ufw allow 80/tcp
ufw reload
```

## 12. 日常最短检查清单

香橙派开机后执行：

```sh
hostname -I
systemctl is-active nginx
systemctl is-active photo-ai
systemctl is-active photo-ai-modelarts-tunnel
curl -I http://127.0.0.1/
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:18000/health
```

随后在手机打开：

```text
http://香橙派IP/
```

验收标准：网页打开、选图成功、YOLO 返回、AI 深度分析返回。实时摄像头是否可用另由 HTTPS 条件决定。
