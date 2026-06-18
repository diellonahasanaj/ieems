import cv2
import easyocr
import numpy as np

reader = easyocr.Reader(['en'], gpu=False)


def preprocess_image(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)

    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    processed = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return processed


def extract_text_and_boxes(image_path: str):
    processed_img = preprocess_image(image_path)

    results = reader.readtext(processed_img)

    text_lines = []
    boxes = []
    confidences = []

    for bbox, text, prob in results:
        text_lines.append(text)

        boxes.append({
            "text": text,
            "box": [[int(p[0]), int(p[1])] for p in bbox],
            "confidence": float(prob)
        })

        confidences.append(float(prob))

    avg_conf = (
        sum(confidences) / len(confidences)
        if confidences else 0.0
    )

    return (
        "\n".join(text_lines),
        boxes,
        avg_conf
    )