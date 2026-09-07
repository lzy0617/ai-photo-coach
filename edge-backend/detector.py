import os
import time
import tempfile
import threading

import numpy as np
from PIL import Image, ImageOps

from acllite_resource import AclLiteResource
from acllite_model import AclLiteModel
from acllite_imageproc import AclLiteImageProc
from acllite_image import AclLiteImage

from label import labels


class AscendYoloDetector:
    def __init__(
        self,
        model_path,
        model_width=640,
        model_height=640,
        person_only=True
    ):
        self.model_path = model_path
        self.model_width = model_width
        self.model_height = model_height
        self.person_only = person_only

        # 第一版串行访问 NPU，最稳定
        self.lock = threading.Lock()

        print("[YOLO] Initializing Ascend resources...")

        self.resource = AclLiteResource()
        self.resource.init()

        self.dvpp = AclLiteImageProc(self.resource)
        self.model = AclLiteModel(self.model_path)

        print("[YOLO] Model loaded successfully.")


    def _prepare_image(self, image_path):
        """
        将任意 JPG/JPEG：
        1. 应用 EXIF 方向
        2. 转 RGB
        3. 保持比例缩放
        4. letterbox 到 640x640
        5. 保存为 baseline JPEG

        返回：
        temp_path
        原图宽高
        scale
        pad_x / pad_y
        """

        image = Image.open(image_path)

        # 修正手机 EXIF 方向
        image = ImageOps.exif_transpose(image)

        image = image.convert("RGB")

        original_width, original_height = image.size

        scale = min(
            self.model_width / original_width,
            self.model_height / original_height
        )

        resized_width = round(
            original_width * scale
        )

        resized_height = round(
            original_height * scale
        )

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS

        resized = image.resize(
            (resized_width, resized_height),
            resample
        )

        # YOLO 常用 114 灰色 padding
        canvas = Image.new(
            "RGB",
            (
                self.model_width,
                self.model_height
            ),
            (114, 114, 114)
        )

        pad_x = (
            self.model_width - resized_width
        ) // 2

        pad_y = (
            self.model_height - resized_height
        ) // 2

        canvas.paste(
            resized,
            (pad_x, pad_y)
        )

        f = tempfile.NamedTemporaryFile(
            suffix=".jpg",
            delete=False
        )

        temp_path = f.name
        f.close()

        canvas.save(
            temp_path,
            format="JPEG",
            quality=95,
            progressive=False,
            subsampling=2
        )

        return {
            "path": temp_path,

            "original_width":
                original_width,

            "original_height":
                original_height,

            "scale":
                scale,

            "pad_x":
                pad_x,

            "pad_y":
                pad_y
        }


    def detect(self, image_path):
        with self.lock:

            total_start = time.perf_counter()

            prepared = None

            try:
                # -------------------------
                # 图像规范化
                # -------------------------

                t0 = time.perf_counter()

                prepared = self._prepare_image(
                    image_path
                )

                clean_path = prepared["path"]

                preprocess_cpu_ms = (
                    time.perf_counter() - t0
                ) * 1000

                # -------------------------
                # DVPP JPEG decode
                # -------------------------

                t1 = time.perf_counter()

                frame = AclLiteImage(
                    clean_path
                )

                yuv_image = self.dvpp.jpegd(
                    frame
                )

                # 已经是 640x640。
                # 继续调用 resize 以保持与官方模型
                # 输入流程一致。
                resized_image = self.dvpp.resize(
                    yuv_image,
                    self.model_width,
                    self.model_height
                )

                dvpp_ms = (
                    time.perf_counter() - t1
                ) * 1000

                # -------------------------
                # NPU inference
                # -------------------------

                image_info = np.array(
                    [
                        self.model_width,
                        self.model_height,
                        self.model_width,
                        self.model_height
                    ],
                    dtype=np.float32
                )

                t2 = time.perf_counter()

                result = self.model.execute(
                    [
                        resized_image,
                        image_info
                    ]
                )

                infer_ms = (
                    time.perf_counter() - t2
                ) * 1000

                # -------------------------
                # Postprocess
                # -------------------------

                t3 = time.perf_counter()

                box_num = int(
                    result[1][0, 0]
                )

                box_info = (
                    result[0].flatten()
                )

                detections = []

                original_width = (
                    prepared[
                        "original_width"
                    ]
                )

                original_height = (
                    prepared[
                        "original_height"
                    ]
                )

                scale = prepared["scale"]
                pad_x = prepared["pad_x"]
                pad_y = prepared["pad_y"]

                for n in range(box_num):

                    class_id = int(
                        box_info[
                            5 * box_num + n
                        ]
                    )

                    score = float(
                        box_info[
                            4 * box_num + n
                        ]
                    )

                    class_name = labels[
                        class_id
                    ]

                    if (
                        self.person_only
                        and
                        class_name != "person"
                    ):
                        continue

                    # YOLO 输出：
                    # letterbox 640x640
                    # 坐标空间
                    model_x1 = float(
                        box_info[
                            0 * box_num + n
                        ]
                    )

                    model_y1 = float(
                        box_info[
                            1 * box_num + n
                        ]
                    )

                    model_x2 = float(
                        box_info[
                            2 * box_num + n
                        ]
                    )

                    model_y2 = float(
                        box_info[
                            3 * box_num + n
                        ]
                    )

                    # 去掉 letterbox padding，
                    # 再映射回原始图片坐标
                    x1 = (
                        model_x1 - pad_x
                    ) / scale

                    y1 = (
                        model_y1 - pad_y
                    ) / scale

                    x2 = (
                        model_x2 - pad_x
                    ) / scale

                    y2 = (
                        model_y2 - pad_y
                    ) / scale

                    # clip
                    x1 = int(max(
                        0,
                        min(
                            x1,
                            original_width - 1
                        )
                    ))

                    y1 = int(max(
                        0,
                        min(
                            y1,
                            original_height - 1
                        )
                    ))

                    x2 = int(max(
                        0,
                        min(
                            x2,
                            original_width - 1
                        )
                    ))

                    y2 = int(max(
                        0,
                        min(
                            y2,
                            original_height - 1
                        )
                    ))

                    if (
                        x2 <= x1
                        or
                        y2 <= y1
                    ):
                        continue

                    detections.append({
                        "class_id":
                            class_id,

                        "class_name":
                            class_name,

                        "confidence":
                            round(score, 4),

                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2
                        },

                        "bbox_norm": {
                            "x1": round(
                                x1
                                / original_width,
                                4
                            ),

                            "y1": round(
                                y1
                                / original_height,
                                4
                            ),

                            "x2": round(
                                x2
                                / original_width,
                                4
                            ),

                            "y2": round(
                                y2
                                / original_height,
                                4
                            )
                        }
                    })

                postprocess_ms = (
                    time.perf_counter() - t3
                ) * 1000

                total_ms = (
                    time.perf_counter()
                    - total_start
                ) * 1000

                return {
                    "image_width":
                        original_width,

                    "image_height":
                        original_height,

                    "persons":
                        detections,

                    "preprocessing": {
                        "letterbox_scale":
                            round(scale, 6),

                        "pad_x":
                            pad_x,

                        "pad_y":
                            pad_y
                    },

                    "timing": {
                        "normalize_ms":
                            round(
                                preprocess_cpu_ms,
                                2
                            ),

                        "dvpp_ms":
                            round(
                                dvpp_ms,
                                2
                            ),

                        "infer_ms":
                            round(
                                infer_ms,
                                2
                            ),

                        "postprocess_ms":
                            round(
                                postprocess_ms,
                                2
                            ),

                        "total_ms":
                            round(
                                total_ms,
                                2
                            )
                    }
                }

            finally:
                if prepared:
                    try:
                        os.unlink(
                            prepared["path"]
                        )
                    except Exception:
                        pass


    def close(self):
        print(
            "[YOLO] Releasing resources..."
        )

        if hasattr(self, "model"):
            del self.model

        if hasattr(self, "dvpp"):
            del self.dvpp

        if hasattr(self, "resource"):
            del self.resource
