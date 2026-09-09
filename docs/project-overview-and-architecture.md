# 项目功能总结与框架说明

## 1. 项目概述

AI Photo Coach 是一个端云协同的智能人像摄影辅助系统。它通过浏览器获取照片或摄像头画面，在香橙派上使用 YOLO 和传统 CV 快速计算人物位置、画面占比、上方留白与整体亮度，再由用户按需调用华为云上的 Qwen3-VL，补充场景、光线、背景干扰、人物姿态和画面表达建议。

项目的核心原则是：

- 高频、可量化的任务在边缘端完成；
- 低频、语义化的任务在云端完成；
- YOLO/CV 负责几何事实，VLM 不重复修改检测框和构图数值；
- 云端不可用时，边缘端快速分析仍可继续工作；
- VLM 只在用户主动触发时分析一张关键帧，不逐帧调用。

当前主要运行环境：

| 层级 | 运行环境 | 主要技术 |
|---|---|---|
| 浏览器端 | 手机或电脑浏览器 | Vue 3、Web Camera API、Canvas |
| Web 入口 | Orange Pi AI Pro 20T | Nginx |
| 边缘分析 | Ascend 310B1 | FastAPI、ACLLite、YOLOv5s OM、OpenCV |
| 云端分析 | 华为云 ModelArts Ascend 910B3 | FastAPI、PyTorch NPU、Qwen3-VL-8B-Instruct |
| 端云连接 | Orange Pi 到 ModelArts | SSH 本地端口转发、systemd 自动重连 |
| 临时公网入口 | Cloudflare | Quick Tunnel、随机 HTTPS 域名 |

## 2. 用户功能总结

### 2.1 实时摄影指导

“实时指导”面向拍摄前取景，支持：

- 在 HTTPS 或 `localhost` 环境申请浏览器摄像头权限；
- 优先打开后置摄像头，也可以切换前后镜头；
- 设备支持时调整摄像头缩放倍率；
- 在取景画面上显示三分线和人物检测框；
- 周期性截取最长边 640 像素的 JPEG 分析帧；
- 持续调用香橙派 YOLO/CV，反馈人物横向位置、上方留白和主体占比；
- 在连续高分结果后提示当前构图较稳定；
- 网络异常时退避重试，不持续堆积请求；
- 页面切入后台时主动停止摄像头和分析循环；
- 拍摄一张较高质量照片后，自动进入“照片诊断”；
- 切换 `Only YOLO` 与 `AI 深度分析` 模式。

实时模式中的 AI 深度分析仍需用户点击按钮。系统使用当前关键帧和最近一次真实 YOLO/CV 结果调用云端，不会按照视频帧率消耗云端推理资源。

### 2.2 单张照片诊断

“照片诊断”面向拍摄后分析，支持：

- 从相册或文件系统选择 JPG、PNG、WebP 等浏览器可解码图片；
- 在前端拒绝非图片文件和超过 20 MB 的图片；
- 保留原始照片用于预览和下载；
- 生成最长边 640 像素、质量 0.8 的 JPEG 副本用于快速分析；
- 在照片上叠加人物框和三分线；
- 显示构图参考分、主体位置、上方留白、主体占比和整体亮度；
- 提供可执行的中文构图建议；
- 检测不到人物时提示重新取景；
- 多人画面仍展示结果，但明确标记为“单人规则参考”；
- 保存原始照片到浏览器下载位置；
- 按需触发 Qwen3-VL 深度分析。

### 2.3 AI 深度分析

深度分析结合图像与边缘端 metrics，输出：

- 场景类型和场景描述；
- 光线类型、软硬和主要问题；
- 背景质量与干扰物；
- 姿态自然度与姿态问题；
- 画面表达总结；
- 最多 3 条按优先级排序的可执行建议。

前端在等待 VLM 时保留已有 YOLO/CV 结果。超时、网络错误、云端 HTTP 错误或模型 JSON 异常时，边缘接口返回可恢复错误，并附带原始快速分析结果。

### 2.4 服务状态与访问

网页每 30 秒检查一次边缘分析服务，也允许用户手动重试。支持三种访问方式：

- Mac 开发环境：`http://localhost:5173`；
- 局域网正式前端：`http://香橙派IP/`；
- 临时公网 HTTPS：Cloudflare Quick Tunnel 生成的 `https://*.trycloudflare.com`。

## 3. 总体架构

```text
┌──────────────────────────────┐
│ 手机 / 电脑浏览器             │
│ Vue 3、Camera、Canvas、UI     │
└──────────────┬───────────────┘
               │ /health、/api/*
               │ HTTP 或 HTTPS
               ▼
┌──────────────────────────────┐
│ Orange Pi：Nginx :80          │
│ /      → 前端静态文件          │
│ /health、/api/* → FastAPI     │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Orange Pi：FastAPI :8000      │
│ YOLOv5s + 构图规则 + 亮度分析  │
│ VLM Client + 失败降级          │
└──────────────┬───────────────┘
               │ VLM_API_URL
               │ http://127.0.0.1:18000/analyze
               ▼
┌──────────────────────────────┐
│ SSH Tunnel：本地 :18000       │
│ systemd 守护、断线自动重连     │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ ModelArts：FastAPI :8000      │
│ Qwen3-VL-8B-Instruct / NPU    │
└──────────────────────────────┘
```

使用 Cloudflare Quick Tunnel 时，它位于浏览器与 Nginx 之间：

```text
公网浏览器 → Cloudflare HTTPS → cloudflared → 127.0.0.1:80 → Nginx
```

Cloudflare 不直接连接边缘 FastAPI 的 `8000` 端口，因为那样会绕过静态网页入口和 Nginx 的同源代理。

## 4. 各层职责

### 4.1 浏览器前端

前端位于 `frontend/`，使用 Vue 3 和 Vite。

主要职责：

- 摄像头生命周期、前后镜头与可选缩放控制；
- 相册选图、图片格式和大小校验；
- Canvas 抓帧与 JPEG 压缩；
- 实时分析循环、失败退避和画面稳定判定；
- 人物框、三分线、构图结果和深度建议展示；
- 快速分析与深度分析的前端请求互斥；
- 处理超时、断网、非法响应和迟到响应；
- 页面切换、资源释放和对象 URL 清理。

前端默认使用相对路径访问 `/health` 和 `/api/*`。开发环境由 Vite 代理，部署环境由 Nginx 代理。

### 4.2 Nginx Web 入口

Nginx 运行在香橙派 `80` 端口，承担：

- 从 `/var/www/photo-ai` 返回前端构建产物；
- 使用 `try_files` 支持单页应用入口；
- 将 `/health` 转发到边缘 FastAPI；
- 将 `/api/*` 转发到边缘 FastAPI；
- 设置上传大小和长请求超时；
- 作为局域网 IP 和 Cloudflare Tunnel 的统一 origin。

Nginx 不执行 YOLO 或 VLM 推理。

### 4.3 香橙派边缘后端

边缘后端位于 `edge-backend/`，部署时对应香橙派 `/root/photo-ai/backend/`。

主要职责：

- 启动时初始化 ACLLite 和 YOLO OM 模型；
- 将手机图片应用 EXIF 方向、转 RGB、按比例缩放并 letterbox 到 `640 × 640`；
- 使用 DVPP 解码/缩放和 Ascend 310B1 执行 YOLO 推理；
- 将检测框从模型坐标映射回原图坐标；
- 当前只保留 `person` 类别；
- 通过线程锁串行访问边缘 NPU；
- 计算构图规则、整体亮度和推理耗时；
- 校验前端提交的 metrics；
- 将深度请求转发给 VLM 并统一响应格式；
- 深度分析失败时保留快速分析结果。

### 4.4 构图与亮度规则

构图模块根据人物检测框计算：

- 人物中心与左、右三分线及画面中心的距离；
- 人物顶部到画面顶部的留白比例；
- 人物检测框面积占整张图的比例；
- 主体位置、上方留白、主体占比三个维度分数；
- 面向用户的移动、靠近、远离或调整取景建议。

多人时使用 `检测框面积 × confidence` 选择主要主体。当前规则以单人人像为目标，多人结果只作为位置参考。

亮度模块使用灰度均值、极暗像素比例和接近纯白像素比例描述整体明暗。亮度统计不计入构图参考分，因为明暗可能是摄影创作选择。

### 4.5 边缘 VLM Client

`edge-backend/services/vlm_client.py` 是边缘端唯一的云端适配层：

- 从 `VLM_API_URL` 读取 VLM 地址；
- 默认请求 `http://127.0.0.1:18000/analyze`；
- 将字段转换为云端所需的 `image` 和 `cv_metrics`；
- 设置连接池和 90 秒 HTTP 超时；
- 解析标准 JSON、Markdown JSON 代码块及常见模型服务包装结构；
- 将不同云端响应归一化为统一摄影分析结构；
- 将超时、连接失败和格式错误映射为稳定错误码。

### 4.6 ModelArts 云端 VLM

云端服务位于 `cloud-vlm/`，主要职责：

- 启动时只加载一次 Qwen3-VL-8B-Instruct；
- 使用 `bfloat16` 和 Ascend NPU 推理；
- 校验图片、`cv_metrics` 和大小限制；
- 修正 EXIF 方向并将图像缩小到最长边 1280 像素；
- 在 Prompt 中明确 YOLO/CV 数据是几何事实；
- 要求模型只返回结构化 JSON；
- 使用异步锁串行执行单卡推理；
- 最多生成 768 个新 token；
- 返回场景、光线、背景、姿态、表达和建议。

### 4.7 SSH Tunnel

ModelArts API 在开发阶段只监听云端 `127.0.0.1:8000`，不直接暴露公网。香橙派通过 SSH 本地端口转发获得：

```text
香橙派 127.0.0.1:18000 → ModelArts 127.0.0.1:8000
```

`photo-ai-modelarts-tunnel.service` 负责开机启动、连接保活和断线重连。Nginx 和浏览器不需要知道 ModelArts 的 SSH 地址、端口或 PEM 信息。

## 5. 核心数据流

### 5.1 快速分析

```text
照片或摄像头帧
  → 浏览器缩放压缩为 JPEG
  → POST /api/analyze-fast
  → Nginx 转发到边缘 FastAPI
  → YOLO 人物检测
  → 构图规则 + 亮度统计
  → JSON 返回浏览器
  → 人物框、评分和建议展示
```

快速分析完全在浏览器和香橙派之间完成，不依赖云端 Qwen。

### 5.2 深度分析

```text
用户点击 AI 深度分析
  → 当前关键帧 + 最近一次真实 YOLO/CV metrics
  → POST /api/deep-analyze
  → 边缘端校验并转发
  → SSH Tunnel
  → POST ModelArts /analyze
  → Qwen3-VL 单卡串行推理
  → 边缘端归一化响应
  → 浏览器展示深度建议
```

前端快速请求和深度请求使用不同的互斥状态，因此等待云端期间，实时 YOLO 循环仍可继续。

### 5.3 深度分析失败降级

```text
VLM 超时 / 断线 / HTTP 错误 / JSON 异常
  → 边缘端捕获 VLMError
  → success: false
  → 返回错误码、友好提示和 fast_analysis
  → 前端保留 YOLO/CV 结果
```

## 6. HTTP 接口

### 6.1 边缘端接口

| 方法 | 路径 | 输入 | 作用 |
|---|---|---|---|
| GET | `/health` | 无 | 检查 Orange Pi、Ascend 和 YOLO 服务 |
| POST | `/api/analyze-fast` | multipart `image` | YOLO、构图和亮度快速分析 |
| POST | `/api/deep-analyze` | multipart `image`、`metrics` | 转发一张关键帧和已有 CV 数据到云端 |

`/api/deep-analyze` 的 `metrics` 是 JSON 字符串，必须包含人物数组和 `composition`。图片不能为空且不能超过 20 MB。

快速分析主要返回：

```text
mode
backend
image
detection.persons
composition
brightness
suggestions
timing
```

深度分析成功主要返回：

```text
success
mode
fast_analysis
deep_analysis
```

### 6.2 云端接口

| 方法 | 路径 | 输入 | 作用 |
|---|---|---|---|
| GET | `/health` | 无 | 检查模型加载状态和 NPU 设备 |
| POST | `/analyze` | multipart `image`、`cv_metrics` | 执行 Qwen3-VL 摄影语义分析 |

注意字段名不同：浏览器调用边缘端时使用 `metrics`，边缘端调用云端时使用 `cv_metrics`。

## 7. 运行进程与端口

| 位置 | 服务 | 端口 | 暴露范围 |
|---|---|---:|---|
| Orange Pi | Nginx | 80 | 局域网；可由 Cloudflare 转发 |
| Orange Pi | Edge FastAPI | 8000 | Nginx 上游；当前也监听全部网卡 |
| Orange Pi | SSH 本地转发 | 18000 | 仅 `127.0.0.1` |
| ModelArts | Qwen FastAPI | 8000 | 仅云端 `127.0.0.1` |
| Mac 开发环境 | Vite | 5173 | 本地开发或指定网卡 |

香橙派当前服务关系：

```text
nginx.service
photo-ai.service
photo-ai-modelarts-tunnel.service
```

临时公网演示时，再以前台方式运行：

```sh
cloudflared tunnel --url http://127.0.0.1:80
```

## 8. 项目目录

```text
ai-photo-coach/
├── frontend/                         # Vue 3 浏览器端
│   ├── src/api/photography.js        # API、超时与请求互斥
│   ├── src/composables/              # 摄像头和摄影分析状态
│   ├── src/components/               # 人物框、评分、建议等组件
│   ├── src/views/                    # 实时指导与照片诊断
│   ├── src/utils/                    # 压缩、展示、稳定性与保存逻辑
│   └── tests/                        # Node 单元测试
├── edge-backend/                     # Orange Pi FastAPI
│   ├── app.py                        # 健康、快速分析、深度分析接口
│   ├── detector.py                   # ACLLite / Ascend YOLO
│   ├── composition.py                # 人像构图几何规则
│   ├── image_quality.py              # 整体亮度统计
│   ├── services/vlm_client.py        # 云端 VLM 适配与归一化
│   └── tests/                        # 深度接口和客户端测试
├── cloud-vlm/                        # ModelArts Qwen3-VL FastAPI
│   ├── app.py
│   ├── requirements.txt
│   └── tests/
├── deploy/orangepi/                  # 自动 SSH Tunnel 安装文件
└── docs/                              # 部署、访问与排障文档
```

仓库目录名 `edge-backend/` 在香橙派部署时对应 `/root/photo-ai/backend/`，不要把两者误认为两个不同服务。

## 9. 并发、性能与资源策略

- 浏览器端保证同一时间只有一个快速分析请求在途，避免实时、模拟和照片诊断共同挤压边缘 NPU；
- 深度分析使用独立互斥锁，重复点击不会产生多条相同云端任务；
- 边缘 YOLO 使用线程锁串行访问 ACLLite/NPU；
- 云端 Qwen 使用异步锁串行访问一张 NPU 卡；
- 实时分析使用 640 像素 JPEG，降低网络传输和推理开销；
- 云端将图片进一步限制在最长边 1280 像素；
- 网络连续失败时，实时循环逐步延长重试间隔，最长约 5 秒；
- 边缘 VLM Client 超时为 90 秒，前端深度请求超时为 120 秒；
- Cloudflare 代理存在额外超时限制，因此长期运行更适合异步深度任务。

## 10. 容错设计

| 故障 | 系统行为 |
|---|---|
| 摄像头权限被拒绝 | 显示对应浏览器权限提示 |
| 相机被占用或不存在 | 停止会话并显示可操作错误 |
| 边缘服务暂时无响应 | 清除旧框、显示等待状态并退避重试 |
| 页面进入后台 | 释放摄像头，停止分析循环 |
| 图片不可解码或超过限制 | 前端或后端拒绝请求并给出提示 |
| 未检测到人物 | 不输出正常人像评分，提示调整取景 |
| 检测到多人 | 选择主主体计算，并标记单人规则限制 |
| SSH Tunnel 或云端失败 | 深度分析降级，快速分析继续可用 |
| VLM 输出不是有效 JSON | 边缘端尝试解包；仍失败则返回格式异常 |
| 快速/深度重复请求 | 由前端互斥逻辑合并或拒绝 |

## 11. 测试与验证

边缘后端测试：

```sh
cd edge-backend
pytest -q
```

云端接口测试：

```sh
cd cloud-vlm
pytest -q
```

前端测试与构建：

```sh
cd frontend
npm ci
npm test
npm run build
```

单元测试覆盖 VLM 响应归一化、错误降级、接口输入、图片压缩、相机生命周期、实时稳定性、检测框映射、结果展示和照片保存等逻辑。真实 NPU、ModelArts、SSH Tunnel、手机摄像头和公网访问仍需要设备联调。

## 12. 当前边界与限制

- 当前构图规则主要面向单人人像，不是通用摄影美学评分器；
- YOLO 只保留人物类别，不识别全部背景物体；
- 构图参考分只反映人物位置、画面占比和留白关系；
- 亮度统计是全局灰度统计，不等于面部测光、动态范围或曝光审美判断；
- VLM 的场景和审美建议具有生成模型的不确定性；
- 深度分析是同步长请求，可能受到浏览器、代理和 Cloudflare 超时影响；
- ModelArts Notebook 和 Quick Tunnel 适合开发或演示，不是稳定生产服务；
- Quick Tunnel 随机地址没有应用身份认证，知道地址的人可以访问接口；
- 当前边缘 FastAPI 配置允许任意 CORS 来源，正式公网部署前应收紧；
- 项目尚未实现账号、配额、持久化任务、审计日志和正式监控告警。

## 13. 后续演进方向

建议按优先级推进：

1. 为正式公网入口配置固定域名、可信 HTTPS 和 Cloudflare Access；
2. 将边缘 FastAPI 仅绑定本机或通过防火墙限制，只允许 Nginx访问；
3. 将深度分析改为任务提交、状态查询和结果获取，避免长连接超时；
4. 增加请求鉴权、速率限制、上传配额和结构化日志；
5. 将 Qwen3-VL 从 Notebook 迁移到稳定推理服务；
6. 增加人脸受光、背景边缘、水平线和更多构图规则；
7. 使用真实拍摄数据建立建议准确性和延迟评测集；
8. 增加端到端浏览器测试和设备启动后的自动健康检查。

## 14. 相关文档

- [Mac 本地网页完整启用流程](mac-local-service-guide.md)
- [香橙派自动连接 ModelArts VLM](orangepi-auto-ssh-tunnel.md)
- [通过香橙派 IP 访问网页](orangepi-web-ip-access.md)
- [Cloudflare 临时域名访问流程](cloudflare-quick-tunnel.md)
- [云端 Qwen3-VL 部署说明](../cloud-vlm/README.md)
