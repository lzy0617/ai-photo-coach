import cv2
import numpy as np


def analyze_brightness(image_path):
    image = cv2.imread(image_path)

    if image is None:
        return {
            "status": "error",
            "score": 0,
            "comment": "无法读取图片"
        }

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    mean_value = float(
        np.mean(gray)
    )

    # 极暗 / 极亮像素比例
    dark_ratio = float(
        np.mean(gray < 25)
    )

    highlight_ratio = float(
        np.mean(gray > 245)
    )

    if mean_value < 55:
        score = 45
        tendency = "dark"
        comment = (
            "画面整体偏暗，"
            "可尝试提高曝光或增加光线"
        )

    elif mean_value < 85:
        score = 70
        tendency = "slightly_dark"
        comment = (
            "画面整体略暗"
        )

    elif mean_value <= 190:
        score = 100
        tendency = "normal"
        comment = (
            "整体亮度较自然"
        )

    elif mean_value <= 220:
        score = 75
        tendency = "slightly_bright"
        comment = (
            "画面整体略亮"
        )

    else:
        score = 45
        tendency = "bright"
        comment = (
            "画面整体偏亮，"
            "建议注意高光区域"
        )

    # 如果大量高光已经接近纯白，
    # 再额外提醒
    if highlight_ratio > 0.12:
        score = min(
            score,
            65
        )

        comment += (
            "；存在较多接近过曝的高光区域"
        )

    if dark_ratio > 0.30:
        score = min(
            score,
            65
        )

        comment += (
            "；暗部区域占比较高"
        )

    return {
        "status": "ok",
        "score": score,

        "mean_brightness":
            round(mean_value, 2),

        "dark_ratio":
            round(dark_ratio, 4),

        "highlight_ratio":
            round(
                highlight_ratio,
                4
            ),

        "tendency":
            tendency,

        "comment":
            comment
    }
