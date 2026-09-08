# AI Photo Coach 前端

Vue 3 + Vite 手机端 Web MVP。运行环境：Node.js 20.19+ 或 22.12+（已在 Node.js 24 下验证）。

## 本地启动

```sh
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

电脑访问终端显示的本地地址。手机与电脑连接同一局域网，访问终端显示的 Network 地址，默认端口 5173。手机上的 localhost 指手机自身。

## API 配置

默认 `VITE_API_BASE` 为空，请求同源的 `/health` 和 `/api/analyze-fast`。

开发时推荐在 `.env.local` 配置代理：

```dotenv
VITE_API_BASE=
API_PROXY_TARGET=http://192.168.1.100:8000
```

也可以直接配置手机可访问的边缘端地址：

```dotenv
VITE_API_BASE=http://192.168.1.100:8000
```

地址仅为示例，请替换为实际设备地址。直连需要后端允许前端来源的 CORS；现有后端已允许所有来源。HTTPS 前端需要 HTTPS API，或通过同源反向代理转发，避免浏览器拦截混合内容。

Vite 环境变量在构建时注入。修改后需要重启开发服务或重新构建；不要在 `VITE_` 变量中放密钥。`API_PROXY_TARGET` 只用于开发，不会配置生产服务器。

## 构建与检查

```sh
npm test
npm run build
npm run preview
```

输出目录是 `frontend/dist/`。将其部署到静态服务器根目录。若 `VITE_API_BASE` 为空，生产服务器需将 `/api/` 和 `/health` 反向代理到边缘后端；仅部署静态文件不会提供分析 API。

## 结构

- `src/api/photography.js`：统一 API 地址、超时、请求错误及快速/深度请求互斥。
- `src/composables/usePhotography.js`：两个 Tab 共用照片、结果、上传校验及重试状态。
- `src/composables/useCamera.js`：getUserMedia、等比例 640px JPEG 抓帧、媒体轨道释放及迟到权限结果保护。
- `src/components/PhotoViewer.vue`、`CompositionOverlay.vue`：按原始比例显示照片与归一化覆盖层，支持开关三分线和人物框。
- `src/components/ImageUploader.vue`：拍照 / 相册入口，最大 20 MB；浏览器不能解码的图片提示转换格式。
- `src/components/ScoreCard.vue`、`SuggestionCard.vue`、`AppIcon.vue`：可复用展示组件和内联 SVG 图标。
- `src/views/LiveGuide.vue`、`PhotoAnalysis.vue`：即时指导和详细诊断。
- `src/utils/overlay.js`：归一化坐标优先、像素坐标回退和边界校验。

没有内置假分析数据。未连接 Edge 时保留完整页面，显示真实离线状态。无人物时隐藏评分，而非显示零分；亮度只作为状态，忽略后端亮度 score。

照片上传后自动分析，切换 Tab 保留照片与结果。拍照入口使用文件输入的 `capture` 提示，实际行为由浏览器决定。实时指导已接入摄像头；选择 `AI 深度分析` 后，由用户点击按钮按需抓取一帧并携带最近一次 YOLO/CV 结果调用边缘端。照片诊断也可在快速分析完成后按需请求。摄像头需要 HTTPS 或 localhost；手机访问普通局域网 HTTP 地址不能启用摄像头。

## 设备联调清单

1. `/health` 正常时显示 Edge 在线；断网后点击状态按钮可复查。
2. 上传横图和竖图，确认人物框、中心点与照片对齐，切换辅助线不改变照片尺寸。
3. 上传无人照片，确认友好提示且不显示零分。
4. 分析中显示等待状态；断网或服务器报错后可对当前照片重试。
5. 在手机相册和相机验证实际照片格式、EXIF 方向与边缘端解码方向一致。

坐标逻辑有自动测试；真实 NPU 推理、手机相机与跨设备网络需连接设备后完成上述联调。

## 实时指导

点击「开启实时指导」申请摄像头权限，优先后置摄像头，不申请音频。视频保持连续播放，循环只更新检测框和一条优先建议，不显示整屏 loading。

- 串行执行：抓帧 → 等待快速分析 → 更新结果 → 等待 250ms → 下一帧。失败后等待 1、2、4、5 秒（上限）再试，保持摄像头开启。
- 分析帧长边最多 640px，JPEG quality 0.75，保持比例、不裁剪、不补边、不放大。
- 所有快速分析调用共享互斥锁。暂停不会强行中断已发出的请求，而是忽略其结果；重启或照片分析等待旧请求结束。尚未发送的已取消会话不会发出请求。
- 暂停、切换 Tab、页面进入后台或卸载均停止轨道与后续抓帧。再次开启需要点击按钮；权限弹窗迟到返回的流也会释放。
- 视频容器按 videoWidth / videoHeight 定比，video 与 Overlay 共用矩形，使用 contain、不镜像。设备旋转时清除旧检测框。框来自最近完成分析的帧，运动时会有网络与推理带来的时间延迟。
- 开发控制台记录帧尺寸、JPEG 字节数、调用往返耗时（包含可能的互斥等待）与后端 total_ms。
- `Only YOLO` 不触发云端请求；`AI 深度分析` 也不会按帧调用。深度请求在途时按钮显示 loading，重复点击复用同一请求；失败只显示深度分析错误，摄像头和实时 YOLO 循环继续运行。

真机检查：允许/拒绝权限、横竖屏旋转、快速暂停再开启、分析中切换 Tab、后台再返回、Edge 断网后恢复；Network 面板确认 analyze-fast 请求不重叠。自动测试覆盖请求互斥和错误释放、迟到摄像头权限、抓帧缩放与建议优先级；真实摄像头和 Tunnel 延迟需设备验证。

## 相机操作

- 快门：`capturePhoto(video)` 保存原始视频帧尺寸，JPEG quality 0.92（不保证达到手机原生相机的静态照片分辨率）。拍摄成功后暂停实时指导，切换到照片诊断并复用 `selectFile`。原照片留作预览，Edge 仍只接收 `prepareFastImage` 的 640px 副本。
- 实时分析：`capture(video)` 保持 640px / JPEG 0.75，不作为最终照片。快门不等待在途 Edge 请求；诊断请求依靠已有全局互斥等待，避免重叠上传。
- Zoom：仅在 track 提供有效 zoom 范围及 applyConstraints 时显示控件，使用真实硬件约束。能力缺失或约束失败会隐藏缩放控件，保留预览、YOLO 和快门。不使用 CSS 缩放。
- 切换镜头：先暂停旧会话并释放轨道，再用 environment / user 的 ideal 偏好重启。请求 1920×1080 ideal 分辨率，实际分辨率由设备决定。若设备提供实际 facingMode 则展示逻辑以实际值为准；没有所选镜头时保留可用镜头并提示（部分浏览器不提供镜头方向信息）。

真机补充检查：Edge 请求期间立即按快门、诊断预览原始尺寸、前后镜头切换、缩放后的画面/人物框/照片一致性，以及 iOS 等不支持网页缩放设备上的基本拍摄流程。
