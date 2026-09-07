import cv2


def draw_analysis(
    image_path,
    detection,
    output_path
):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Cannot read image: {image_path}"
        )

    h, w = image.shape[:2]

    # 三分线
    x_left = int(w / 3)
    x_right = int(w * 2 / 3)
    y_top = int(h / 3)
    y_bottom = int(h * 2 / 3)

    cv2.line(
        image,
        (x_left, 0),
        (x_left, h),
        (255, 255, 255),
        2
    )

    cv2.line(
        image,
        (x_right, 0),
        (x_right, h),
        (255, 255, 255),
        2
    )

    cv2.line(
        image,
        (0, y_top),
        (w, y_top),
        (255, 255, 255),
        2
    )

    cv2.line(
        image,
        (0, y_bottom),
        (w, y_bottom),
        (255, 255, 255),
        2
    )

    for person in detection["persons"]:
        box = person["bbox"]

        x1 = box["x1"]
        y1 = box["y1"]
        x2 = box["x2"]
        y2 = box["y2"]

        # 人物框
        cv2.rectangle(
            image,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            4
        )

        # 中心
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        cv2.circle(
            image,
            (cx, cy),
            10,
            (0, 0, 255),
            -1
        )

        label = (
            f"person "
            f"{person['confidence']:.2f}"
        )

        cv2.putText(
            image,
            label,
            (x1, max(y1 - 15, 30)),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

    cv2.imwrite(
        output_path,
        image
    )

    return output_path
