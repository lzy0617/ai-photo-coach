# AI Photo Coach

端云协同的智能摄影辅助系统。Orange Pi 使用 YOLO/CV 提供连续的实时构图建议；用户按需触发 AI 深度分析时，边缘端再将一张 JPEG 关键帧和最近一次真实 metrics 转发给云端 Qwen3-VL。

## 目录

```text
ai-photo-coach/
├── edge-backend/
│   ├── app.py                    # FastAPI、快速分析与深度分析路由
│   ├── composition.py            # 构图几何分析
│   ├── detector.py               # Ascend YOLO 推理
│   ├── image_quality.py          # 亮度分析
│   ├── services/
│   │   └── vlm_client.py         # 云端请求、错误映射与响应归一化
│   ├── tests/                    # VLM client 与深度接口测试
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/api/photography.js    # 快速/深度 API 与请求互斥
│   ├── src/components/DeepAnalysisCard.vue
│   ├── src/views/LiveGuide.vue   # Only YOLO / AI 深度分析
│   ├── src/views/PhotoAnalysis.vue
│   └── tests/
├── cloud-vlm/                    # ModelArts Qwen3-VL /analyze 服务
└── docs/
```

## 启动 Orange Pi 后端

先进入已经加载 Ascend/acllite 运行环境的终端，并确认 `detector.py` 中现有 OM 模型路径有效：

```sh
cd edge-backend
python3 -m pip install -r requirements.txt
export VLM_API_URL=http://127.0.0.1:18000/analyze
uvicorn app:app --host 0.0.0.0 --port 8000
```

`VLM_API_URL` 是唯一的 VLM 地址来源。开发期可指向 Orange Pi 上 SSH Tunnel 的本地端口，将来可直接改成正式 HTTPS `/analyze` 地址；项目代码不包含 SSH 建连逻辑。

## 深度分析调用

先从 `/api/analyze-fast` 取得真实结果并保存为 `metrics.json`，再调用：

```sh
curl -X POST http://127.0.0.1:8000/api/deep-analyze \
  -F 'image=@test.jpg;type=image/jpeg' \
  -F 'metrics=<metrics.json'
```

边缘端向云端发送的字段为 `image` 和 `cv_metrics`。VLM 超时、连接失败、HTTP 错误或非法输出时，接口以 `success: false` 返回原始 `fast_analysis`，不会改变 `/api/analyze-fast` 的行为。

## 测试

```sh
cd edge-backend
pytest -q

cd ../frontend
npm ci
npm test
npm run build
```

后端单元测试使用假的 VLM 和假的 Ascend detector，不需要 NPU。真实 ModelArts、SSH Tunnel、Orange Pi NPU、浏览器摄像头和移动网络仍需在对应设备上联调。

完整的 Mac 本地端云启动顺序、环境变量、验收和故障排查见 [`docs/mac-local-service-guide.md`](docs/mac-local-service-guide.md)。
