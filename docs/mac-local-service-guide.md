# Mac 本地网页完整启用流程

本文说明如何在 Mac 上启动 AI Photo Coach 前端，并连接香橙派上的 YOLO/CV 后端和华为云 ModelArts 上的 Qwen3-VL。

## 1. 系统结构

```text
Mac 浏览器（摄像头和网页）
    │
    │ Vite 开发代理
    ▼
香橙派 FastAPI :8000
    ├── /api/analyze-fast  → 本机 YOLO + CV 实时分析
    └── /api/deep-analyze
             │
             │ VLM_API_URL=http://127.0.0.1:18000/analyze
             ▼
       SSH Tunnel :18000
             │
             ▼
华为云 ModelArts Qwen3-VL API 127.0.0.1:8000
```

运行时共有四个前台进程：

1. 华为云上的 Qwen3-VL FastAPI；
2. 香橙派上的 SSH Tunnel；
3. 香橙派上的 YOLO/CV FastAPI；
4. Mac 上的 Vite 前端。

任意一个进程停止，相关功能就会不可用。云端或 Tunnel 停止只影响 AI 深度分析，不应影响 Only YOLO。

## 2. 已部署目录

华为云 ModelArts：

```text
/home/ma-user/work/
├── cloud-vlm/
│   ├── app.py
│   └── requirements.txt
├── models/Qwen3-VL-8B-Instruct/
└── test.jpg
```

香橙派：

```text
/root/photo-ai/
├── backend/
│   ├── app.py
│   ├── detector.py
│   ├── composition.py
│   ├── image_quality.py
│   ├── models/
│   └── services/
│       ├── __init__.py
│       └── vlm_client.py
├── frontend/dist/
├── scripts/
└── test.jpg
```

Mac：

```text
/Users/reiayanami/Documents/Note/huaweicloud/ai-photo-coach/
├── frontend/
├── edge-backend/
├── cloud-vlm/
└── docs/
```

## 3. 启动前准备

需要提前知道以下信息：

- 香橙派局域网 IP，例如 `192.168.1.100`；
- ModelArts SSH 域名，例如 `authoring-ssh-modelarts-xxxxx.huawei.com`；
- ModelArts SSH 外部端口，例如 `31092`；
- ModelArts PEM 密钥在香橙派上的路径，例如 `/root/.ssh/modelarts.pem`。

在香橙派查看局域网 IP：

```sh
hostname -I
```

本文中的示例 IP、SSH 域名和端口必须替换成实际值。复制命令时，URL 直接写成 `http://...`，不要带 Markdown 的方括号、圆括号或反斜杠。

## 4. 第一步：启动华为云 Qwen3-VL API

进入 ModelArts Notebook 的 Terminal：

```sh
cd /home/ma-user/work/cloud-vlm

export QWEN_MODEL_PATH=/home/ma-user/work/models/Qwen3-VL-8B-Instruct
export QWEN_DEVICE=npu:0

uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1
```

注意：

- 模型只应加载一次，不要设置多个 worker；
- 第一次加载可能需要一段时间；
- 保持该 Terminal 开启；
- 不要重新安装或覆盖 `torch`、`torch-npu`、CANN。

另开一个 ModelArts Terminal 验证：

```sh
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{
  "status": "ok",
  "model": "Qwen3-VL-8B-Instruct",
  "device": "npu:0"
}
```

## 5. 第二步：在香橙派建立 SSH Tunnel

确认 PEM 权限：

```sh
chmod 600 /root/.ssh/modelarts.pem
```

在香橙派第一个 Terminal 中启动 Tunnel：

```sh
ssh \
  -i /root/.ssh/modelarts.pem \
  -p 31092 \
  -N \
  -L 127.0.0.1:18000:127.0.0.1:8000 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  ma-user@authoring-ssh-modelarts-xxxxx.huawei.com
```

需要替换：

- `31092`：ModelArts 控制台显示的 SSH 外部端口；
- `authoring-ssh-modelarts-xxxxx.huawei.com`：ModelArts SSH 域名；
- PEM 路径：香橙派上的实际密钥位置。

Tunnel 正常时命令不会输出内容，并会一直占用当前 Terminal。

另开一个香橙派 Terminal 验证：

```sh
curl http://127.0.0.1:18000/health
```

它应返回与云端 `/health` 相同的信息。

## 6. 第三步：启动香橙派 YOLO/CV 后端

先设置 Ascend 和 ACLLite 环境：

```sh
source /usr/local/Ascend/ascend-toolkit/set_env.sh

export PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/thirdpart/python:${PYTHONPATH:-}
export VLM_API_URL=http://127.0.0.1:18000/analyze
```

确认关键模块和环境变量：

```sh
/usr/local/miniconda3/bin/python3 -c "import acllite_resource; print(acllite_resource.__file__)"

/usr/local/miniconda3/bin/python3 -c "from services.vlm_client import VLMClient; print('VLMClient OK')"

echo "$VLM_API_URL"
```

启动后端：

```sh
cd /root/photo-ai/backend

/usr/local/miniconda3/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

保持该 Terminal 开启。另开香橙派 Terminal 验证：

```sh
curl http://127.0.0.1:8000/health
```

确认深度接口已加载：

```sh
curl -s http://127.0.0.1:8000/openapi.json | grep -o '/api/deep-analyze'
```

预期输出：

```text
/api/deep-analyze
```

如果端口已经被旧进程占用，先检查：

```sh
ps -ef | grep uvicorn | grep -v grep
```

确认目标是旧后端后，使用普通 `kill PID` 停止，不要直接使用 `kill -9`。

## 7. 第四步：配置并启动 Mac 前端

打开 Mac Terminal：

```sh
cd "/Users/reiayanami/Documents/Note/huaweicloud/ai-photo-coach/frontend"
```

首次运行或依赖有变化时安装依赖：

```sh
npm ci
```

创建本地配置：

```sh
cp -n .env.example .env.local
nano .env.local
```

`.env.local` 必须是两行。将示例 IP 换成香橙派实际 IP：

```dotenv
VITE_API_BASE=
API_PROXY_TARGET=http://192.168.1.100:8000
```

说明：

- `VITE_API_BASE` 故意留空，使浏览器请求 Mac 本机的 Vite 服务；
- Vite 再把 `/health` 和 `/api/*` 转发到香橙派；
- 两个变量不能写在同一行；
- 变量名是 `VITE_API_BASE` 和 `API_PROXY_TARGET`，下划线前没有反斜杠；
- URL 不要写成 `[http://...](http://...)`。

检查配置：

```sh
cat .env.local
```

从 Mac 测试香橙派：

```sh
curl http://192.168.1.100:8000/health
```

启动前端：

```sh
npm run dev
```

浏览器打开：

```text
http://localhost:5173
```

不要在 URL 后添加 Markdown 格式。修改 `.env.local` 后，必须按 `Control+C` 停止 Vite，再重新运行 `npm run dev`。

## 8. 功能验收

### 8.1 照片诊断

1. 打开“照片诊断”；
2. 选择一张人物照片；
3. 确认人物框与人物对齐；
4. 确认出现 YOLO/CV 构图建议；
5. 点击“AI 深度分析”；
6. 确认显示 loading；
7. 确认显示场景、光线、背景、姿态、画面表达和深度建议。

### 8.2 实时指导

1. 打开“实时指导”；
2. 点击“开启实时指导”；
3. 允许浏览器访问摄像头；
4. 确认人物框和实时建议持续更新；
5. 确认 `Only YOLO` 模式不会调用云端；
6. 切换到“AI 深度分析”；
7. 等待至少一次 YOLO 分析完成；
8. 点击“AI 深度分析”；
9. 确认只产生一次深度请求，且实时 YOLO 在等待期间继续工作。

可以在浏览器开发者工具的 Network 面板中观察：

```text
POST /api/analyze-fast
POST /api/deep-analyze
```

### 8.3 容错

临时停止 SSH Tunnel 后点击“AI 深度分析”：

- 页面应提示深度分析暂时不可用；
- 摄像头不能崩溃；
- `/api/analyze-fast` 应继续工作；
- 恢复 Tunnel 后应能重新执行深度分析。

## 9. 后端命令行完整链路测试

在香橙派执行快速分析并保存 metrics：

```sh
curl -s -X POST http://127.0.0.1:8000/api/analyze-fast \
  -F 'image=@/root/photo-ai/test.jpg;type=image/jpeg' \
  -o /root/photo-ai/metrics.json
```

查看 metrics：

```sh
python -m json.tool /root/photo-ai/metrics.json
```

调用香橙派深度接口：

```sh
curl -X POST http://127.0.0.1:8000/api/deep-analyze \
  -F 'image=@/root/photo-ai/test.jpg;type=image/jpeg' \
  -F 'metrics=</root/photo-ai/metrics.json'
```

这里调用香橙派时字段名是 `metrics`；直接调用云端 `/analyze` 时字段名才是 `cv_metrics`。

## 10. 每次开发的最短启动清单

严格按照下面的顺序启动：

1. ModelArts Terminal：启动云端 `uvicorn`；
2. 香橙派 Terminal 1：建立 SSH Tunnel；
3. 香橙派 Terminal 2：设置 Ascend、`PYTHONPATH`、`VLM_API_URL` 并启动后端；
4. Mac Terminal：运行 `npm run dev`；
5. Mac 浏览器：打开 `http://localhost:5173`。

检查顺序：

```text
云端 127.0.0.1:8000/health
  ↓
香橙派 127.0.0.1:18000/health
  ↓
香橙派 127.0.0.1:8000/health
  ↓
Mac curl http://香橙派IP:8000/health
  ↓
Mac http://localhost:5173
```

## 11. 停止服务

开发结束时按相反顺序停止：

1. Mac Vite Terminal 按 `Control+C`；
2. 香橙派后端 Terminal 按 `Control+C`；
3. 香橙派 SSH Tunnel Terminal 按 `Control+C`；
4. ModelArts Qwen API Terminal 按 `Control+C`。

正常停止能让 YOLO/NPU 和 Qwen/NPU 正确释放资源。

## 12. 常见问题

### `curl: (26) Failed to open/read local data`

`@` 后面的图片路径不存在。先检查：

```sh
ls -lh /root/photo-ai/test.jpg
```

然后使用绝对路径。

### `ModuleNotFoundError: acllite_resource`

设置：

```sh
export PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/thirdpart/python:${PYTHONPATH:-}
```

并确认：

```sh
python -c "import acllite_resource; print(acllite_resource.__file__)"
```

### `Address already in use`

检查旧进程：

```sh
ps -ef | grep uvicorn | grep -v grep
ss -lntp | grep 8000
```

### 前端显示无法连接分析服务

依次检查：

```sh
# Mac
curl http://香橙派IP:8000/health

# 香橙派
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:18000/health
```

并确认修改 `.env.local` 后已经重启 `npm run dev`。

### 手机无法打开摄像头

`http://localhost:5173` 只对运行 Vite 的 Mac 本机有效。手机通过普通局域网 HTTP 地址访问时，浏览器通常不会授予摄像头权限。Mac 本地验收完成后，手机部署需要可信 HTTPS，这不属于本文的本地开发启动流程。

## 13. 安全注意事项

- PEM 私钥不要放入项目目录，不要提交 Git；
- 云端 VLM API 开发阶段只监听 `127.0.0.1`；
- 通过 SSH Tunnel 访问云端，不开放无认证的公网 8000 端口；
- `.env.local` 不应提交 Git；
- 不要在 ModelArts 环境中随意升级 `torch`、`torch-npu` 或 CANN；
- 当前流程适合开发和竞赛演示，长期运行应再配置进程守护、自动重连、HTTPS 和访问控制。
