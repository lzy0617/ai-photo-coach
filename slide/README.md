# AI Photo Coach 答辩幻灯片

中文 Beamer，16:9，白底蓝灰配色，13 页。推荐讲述 **9 分钟**（含 1 分钟外部演示），留下约 1 分钟切换与缓冲；不要现场等待完整云端推理。

## 编译

需要带中文支持的 TeX Live / MiKTeX：XeLaTeX、ctex、Beamer、TikZ、listings、latexmk。默认使用 TeX 发行版自带的 Fandol 字体，无须指定操作系统字体，不需要 shell-escape。编译不下载图片或其他素材。

从项目根目录运行：

```sh
cd slide
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build slides.tex
```

结果为 `slide/build/slides.pdf`。没有 latexmk 时，从 `slide/` 运行：

```sh
mkdir -p build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build slides.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build slides.tex
```

务必在 `slide/` 下编译，以便正确解析 `assets/` 相对路径。修改后重复以上命令即可。清理辅助文件并保留 PDF：

```sh
latexmk -c -outdir=build slides.tex
```

## 素材与编辑

所有图片均由 `\asset{文件名}{最大宽度}{最大高度}` 加载，保持原图比例。文件不存在时自动显示灰色占位框及文件名，不阻断编译。要使用其他格式，请同时修改源文件中的扩展名。

| 用途 | `slide/assets/` 下的路径 | 当前情况 |
| --- | --- | --- |
| Orange Pi | `logo_orangepi.png` | 已有 |
| Ascend | `logo_ascend.png` | 已有 |
| YOLO | `logo_yolo.png` | 已有 |
| Qwen | `logo_qwen.png` | 此标准文件名缺失；已自动回退到现有 `log_qwen.png` |
| Vue | `Vue.png` | 已有，注意大小写 |
| FastAPI | `logo_fastapi.png` | 已有 |
| SSH | `ssh.png` | 已有 |
| ModelArts | `logo_modelarts.png` | 已有 |
| 实时指导 | `screenshot_live_advice.png` | 已有 |
| 照片诊断 | `screenshot_photo_analysis.png` | 已有，包含 bbox 与三分线 |
| 深度分析 | `screenshot_deep_analysis.png` | 已有 |
| 外部演示视频（可选） | `demo.mp4` | 尚未提供；不影响编译 |

**无需补充必需图片。** Qwen 优先读取 `logo_qwen.png`，其次读取 `log_qwen.png`；两者都没有时显示标准文件名占位。视频不嵌入 PDF，“项目演示”页仅文字，演示时手动切换外部播放器或网页。若准备视频，建议放在 `assets/demo.mp4`。

封面左下角两条横线各预留 3 个汉字宽度。将 `\makebox[3em]{\hrulefill}` 分别替换为 `\makebox[3em]{张三丰}` 等实际姓名即可。

## 讲述节奏（共 9:00）

| 页 | 内容 | 用时 | 讲述重点 |
| --- | --- | --- | --- |
| 1 | 封面 | 0:20 | 一句话介绍端云分工 |
| 2 | 背景与目标 | 0:40 | 拍摄中及时指导，拍摄后语义理解 |
| 3 | 总体方案：边缘 | 0:40 | 浏览器到 Orange Pi 的快速链路 |
| 4 | 总体方案：云端 | 0:35 | 主动触发、SSH 转发和云端模型 |
| 5 | 实时指导 | 0:45 | 结合截图说明反馈闭环与四类指标 |
| 6 | 构图规则 | 0:45 | bbox 指标如何产生可解释参考 |
| 7 | 深度分析 | 0:45 | 语义评价补充 CV 的能力边界 |
| 8 | 代码 A | 0:35 | await 串行循环避免请求堆积 |
| 9 | 代码 B | 0:30 | 归一化指标与评分权重 |
| 10 | 代码 C | 0:35 | 图像、指标和 JSON 输出约束 |
| 11 | 项目演示 | 1:00 | 实时指导 → 拍摄 → 诊断 → 深度分析 |
| 12 | 问题与优化 | 0:45 | 抓住请求堆积、云端降级等工程问题 |
| 13 | 总结与展望 | 0:45 | 完成项、当前边界和未来方向 |

演示建议：前 20 秒展示实时构图变化，再用 15 秒拍摄并进入照片诊断，最后 25 秒展示事先准备好的深度分析结果。外部视频控制在 60 秒内；若现场切换耗时，缩短演示或问题页讲述。文稿没有虚构延迟、帧率、精度等测试数据。

## 代码出处

幻灯片采用项目代码的教学节选，已标注省略或合并换行，并非可独立执行的完整代码。

- A：`frontend/src/views/LiveGuide.vue` 的 `loop()`，摘录 capture、await analyzeFast、状态更新与 sleep；`start()` 的状态守卫防止重复启动。省略首帧检查、异常退避、方向校验、AbortController 等分支。
- B：`edge-backend/composition.py` 的 `analyze_composition()`；`cx_ratio` 对应 center_x，`headroom_ratio` 对应上方留白，`area_ratio` 对应主体占比。权重为位置 0.45、留白 0.30、主体大小 0.25。
- C：`edge-backend/services/vlm_client.py` 的 HTTP 请求，以及 `cloud-vlm/app.py` 中的图文消息。合法 JSON 的要求来自 `build_prompt()`，输出后还会解析并归一化字段；提示词约束不等同于模型必然生成合法 JSON。
