def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def _select_main_person(persons):
    """
    选择主要摄影主体。

    当前项目主要面向单人人像。
    如果意外检测到多人，用：
        bbox面积 * confidence
    选择最可能的主体。
    """
    if not persons:
        return None

    def importance(person):
        box = person["bbox"]

        width = max(
            0,
            box["x2"] - box["x1"]
        )

        height = max(
            0,
            box["y2"] - box["y1"]
        )

        area = width * height

        return (
            area *
            person.get(
                "confidence",
                1.0
            )
        )

    return max(
        persons,
        key=importance
    )


def analyze_composition(
    image_width,
    image_height,
    persons
):
    """
    根据人物检测框分析最基础的人像构图。

    当前分析：
    1. 主体横向位置
    2. 三分法 / 居中构图
    3. 头顶留白
    4. 人物占画面比例
    5. 给出简单可执行建议
    """

    if not persons:
        return {
            "status": "no_person",
            "score": 0,
            "message": "未检测到人物主体",
            "suggestions": [
                "请确保人物完整出现在画面中"
            ]
        }

    person = _select_main_person(
        persons
    )

    box = person["bbox"]

    x1 = box["x1"]
    y1 = box["y1"]
    x2 = box["x2"]
    y2 = box["y2"]

    W = image_width
    H = image_height

    # -------------------------
    # 主体中心
    # -------------------------

    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    cx_ratio = cx / W
    cy_ratio = cy / H

    # -------------------------
    # 主体大小
    # -------------------------

    person_width = max(
        0,
        x2 - x1
    )

    person_height = max(
        0,
        y2 - y1
    )

    person_area = (
        person_width *
        person_height
    )

    image_area = W * H

    area_ratio = (
        person_area /
        image_area
    )

    # -------------------------
    # 1. 横向构图
    # -------------------------

    left_third = 1 / 3
    right_third = 2 / 3
    center = 0.5

    dist_left = abs(
        cx_ratio -
        left_third
    )

    dist_right = abs(
        cx_ratio -
        right_third
    )

    dist_center = abs(
        cx_ratio -
        center
    )

    nearest_third_distance = min(
        dist_left,
        dist_right
    )

    # 大面积人像居中其实是合理构图，
    # 不应该一律认为“居中就是不好”
    centered_portrait = (
        dist_center <= 0.06
        and
        area_ratio >= 0.18
    )

    if centered_portrait:
        position_score = 95

        position_style = (
            "centered"
        )

        position_comment = (
            "主体接近画面中心，"
            "适合当前较突出的单人人像构图"
        )

        horizontal_suggestion = (
            "主体横向位置基本合适"
        )

    else:
        position_style = (
            "rule_of_thirds"
        )

        if (
            nearest_third_distance
            <= 0.04
        ):
            position_score = 100

            position_comment = (
                "主体非常接近三分线，"
                "横向构图较自然"
            )

        elif (
            nearest_third_distance
            <= 0.08
        ):
            position_score = 85

            position_comment = (
                "主体位置较接近三分线"
            )

        elif (
            nearest_third_distance
            <= 0.14
        ):
            position_score = 65

            position_comment = (
                "主体与三分线有一定距离"
            )

        else:
            position_score = 45

            position_comment = (
                "主体横向位置较难形成"
                "明显的三分构图"
            )

        # 找最近的三分线
        if dist_left < dist_right:
            target_ratio = left_third
        else:
            target_ratio = right_third

        delta_ratio = (
            target_ratio -
            cx_ratio
        )

        if abs(delta_ratio) <= 0.04:
            horizontal_suggestion = (
                "主体横向位置基本合适"
            )

        elif delta_ratio < 0:
            horizontal_suggestion = (
                "建议人物向左移动约 "
                f"{abs(delta_ratio) * 100:.0f}% "
                "画面宽度"
            )

        else:
            horizontal_suggestion = (
                "建议人物向右移动约 "
                f"{abs(delta_ratio) * 100:.0f}% "
                "画面宽度"
            )

    # -------------------------
    # 2. 头顶留白
    # -------------------------

    headroom_ratio = y1 / H

    if (
        0.03
        <= headroom_ratio
        <= 0.15
    ):
        headroom_score = 100

        headroom_comment = (
            "头顶留白较自然"
        )

        headroom_suggestion = None

    elif headroom_ratio < 0.015:
        headroom_score = 45

        headroom_comment = (
            "人物顶部过于贴近画面边缘"
        )

        headroom_suggestion = (
            "建议稍微扩大上方取景范围"
        )

    elif headroom_ratio < 0.03:
        headroom_score = 70

        headroom_comment = (
            "头顶留白略紧"
        )

        headroom_suggestion = (
            "可稍微增加顶部空间"
        )

    elif headroom_ratio <= 0.23:
        headroom_score = 75

        headroom_comment = (
            "顶部留白稍多，但仍可接受"
        )

        headroom_suggestion = (
            "可以适当缩小上方留白"
        )

    else:
        headroom_score = 45

        headroom_comment = (
            "顶部留白较多"
        )

        headroom_suggestion = (
            "建议减少人物上方空白区域"
        )

    # -------------------------
    # 3. 人物占比
    # -------------------------

    if (
        0.18
        <= area_ratio
        <= 0.52
    ):
        subject_size_score = 100

        subject_size_comment = (
            "人物主体占画面比例较合适"
        )

        size_suggestion = None

    elif (
        0.10
        <= area_ratio
        < 0.18
    ):
        subject_size_score = 75

        subject_size_comment = (
            "人物主体略小"
        )

        size_suggestion = (
            "可以适当靠近人物"
        )

    elif area_ratio < 0.10:
        subject_size_score = 45

        subject_size_comment = (
            "人物主体偏小，"
            "视觉重点不够突出"
        )

        size_suggestion = (
            "建议靠近人物或使用更长焦距"
        )

    elif (
        0.52
        < area_ratio
        <= 0.70
    ):
        subject_size_score = 75

        subject_size_comment = (
            "人物占画面比例较大"
        )

        size_suggestion = (
            "如果希望保留环境，"
            "可适当扩大取景范围"
        )

    else:
        subject_size_score = 45

        subject_size_comment = (
            "人物占画面比例过大"
        )

        size_suggestion = (
            "建议稍微远离人物"
        )

    # -------------------------
    # 综合评分
    # -------------------------

    score = round(
        position_score * 0.45
        +
        headroom_score * 0.30
        +
        subject_size_score * 0.25
    )

    score = _clamp(score)

    # -------------------------
    # 汇总建议
    # -------------------------

    suggestions = []

    if (
        horizontal_suggestion
        != "主体横向位置基本合适"
    ):
        suggestions.append(
            horizontal_suggestion
        )

    if headroom_suggestion:
        suggestions.append(
            headroom_suggestion
        )

    if size_suggestion:
        suggestions.append(
            size_suggestion
        )

    if not suggestions:
        suggestions.append(
            "当前基础构图较稳定，"
            "可以进一步关注背景与光线"
        )

    return {
        "status": "ok",

        "score": score,

        "main_subject": {
            "confidence":
                person.get(
                    "confidence"
                ),

            "bbox":
                person["bbox"],

            "center_norm": {
                "x": round(
                    cx_ratio,
                    4
                ),

                "y": round(
                    cy_ratio,
                    4
                )
            },

            "area_ratio":
                round(
                    area_ratio,
                    4
                )
        },

        "position": {
            "score":
                position_score,

            "style":
                position_style,

            "center_x_ratio":
                round(
                    cx_ratio,
                    4
                ),

            "nearest_third_distance":
                round(
                    nearest_third_distance,
                    4
                ),

            "comment":
                position_comment
        },

        "headroom": {
            "score":
                headroom_score,

            "ratio":
                round(
                    headroom_ratio,
                    4
                ),

            "comment":
                headroom_comment
        },

        "subject_size": {
            "score":
                subject_size_score,

            "area_ratio":
                round(
                    area_ratio,
                    4
                ),

            "comment":
                subject_size_comment
        },

        "suggestions":
            suggestions
    }
