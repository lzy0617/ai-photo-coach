# Cloud Qwen3-VL API

在 ModelArts Notebook 的 Ascend 910B3 上，将本地 Qwen3-VL-8B-Instruct 包装成摄影分析接口。服务启动时只加载一次模型，并使用互斥锁串行执行 NPU 推理。

## 部署到 ModelArts

将本目录上传或同步到：

```text
/home/ma-user/work/cloud-vlm
```

在现有 `PyTorch-2.7.1` 环境中执行：

```sh
cd /home/ma-user/work/cloud-vlm
python -m pip install -r requirements.txt

export QWEN_MODEL_PATH=/home/ma-user/work/models/Qwen3-VL-8B-Instruct
export QWEN_DEVICE=npu:0

uvicorn app:app --host 127.0.0.1 --port 8000
```

不要重新安装 `torch`、`torch-npu` 或 CANN。开发阶段监听 `127.0.0.1`，由 SSH Tunnel 转发，不向公网直接暴露无认证接口。

## 云端本机测试

```sh
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/analyze \
  -F 'image=@/home/ma-user/work/test.jpg;type=image/jpeg' \
  -F 'cv_metrics={"detection":{"persons":[]},"composition":{"status":"no_person"}}'
```

服务会返回 `analysis` JSON。香橙派的 normalization 层会将它转换成前端统一结构。
