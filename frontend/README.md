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

- `src/api/photography.js`：统一 API 地址、超时、请求错误、深度点评占位。
- `src/composables/usePhotography.js`：两个 Tab 共用照片、结果、上传校验及重试状态。
- `src/composables/useCamera.js`：预留 getUserMedia、单帧拍摄和媒体轨道释放；尚未连接 UI。
- `src/components/PhotoViewer.vue`、`CompositionOverlay.vue`：按原始比例显示照片与归一化覆盖层，支持开关三分线和人物框。
- `src/components/ImageUploader.vue`：拍照 / 相册入口，最大 20 MB；浏览器不能解码的图片提示转换格式。
- `src/components/ScoreCard.vue`、`SuggestionCard.vue`、`AppIcon.vue`：可复用展示组件和内联 SVG 图标。
- `src/views/LiveGuide.vue`、`PhotoAnalysis.vue`：即时指导和详细诊断。
- `src/utils/overlay.js`：归一化坐标优先、像素坐标回退和边界校验。

没有内置假分析数据。未连接 Edge 时保留完整页面，显示真实离线状态。无人物时隐藏评分，而非显示零分；亮度只作为状态，忽略后端亮度 score。

照片上传后自动分析，切换 Tab 保留照片与结果。拍照入口使用文件输入的 `capture` 提示，实际行为由浏览器决定。实时指导与云端点评按钮为禁用的「即将支持」状态。后续可以将 `useCamera` 与 `analyzeFast` 连接，采用上一请求完成后再采下一帧的方式避免请求堆积。getUserMedia 需要 HTTPS 或 localhost，并需在离开取景时停止媒体轨道。

## 设备联调清单

1. `/health` 正常时显示 Edge 在线；断网后点击状态按钮可复查。
2. 上传横图和竖图，确认人物框、中心点与照片对齐，切换辅助线不改变照片尺寸。
3. 上传无人照片，确认友好提示且不显示零分。
4. 分析中显示等待状态；断网或服务器报错后可对当前照片重试。
5. 在手机相册和相机验证实际照片格式、EXIF 方向与边缘端解码方向一致。

坐标逻辑有自动测试；真实 NPU 推理、手机相机与跨设备网络需连接设备后完成上述联调。
