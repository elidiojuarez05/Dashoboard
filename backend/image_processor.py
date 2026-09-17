import cv2
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import streamlit as st

# 1. Configurar path para encontrar config.py
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

if __name__ == "__main__":
    try:
        print("Prueba de procesador de imagen")
    except NameError as e:
        print(f"Error de prueba: {e}")

# ===============================
# 🔧 AUTO ALIGN (corrige inclinación)
# ===============================
def auto_align_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    lines = cv2.HoughLines(edges, 1, np.pi / 200, 100)
    angle = 0

    if lines is not None:
        angles = []
        for rho, theta in lines[:, 0]:
            deg = (theta * 180 / np.pi) - 90
            angles.append(deg)

        angle = np.median(angles)

    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)

    aligned = cv2.warpAffine(
        img,
        M,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return aligned


# ===============================
# 🔍 AUTO ROI (detecta zona útil)
# ===============================
def detect_roi_auto(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Umbral más alto para ignorar "fantasmas" y sombras
    _, thresh = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return img

    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    my = int(h * 0.015)
    mx = int(w * 0.015)

    return img[y + my:y + h - my, x + mx:x + w - mx]


# ===============================
# 🟣 EPSON (especial)
# ===============================
def process_epson_final(img, config):
    # 1. Preparación
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=4.0,
        tileGridSize=(8, 8)
    )
    gray = clahe.apply(gray)

    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5
    )

    h, w = thresh.shape
    rows = config["rows"]

    # 2. Detección de columnas reales (IA Geométrica)
    v_proj = np.sum(thresh, axis=0) / 255
    ink_mask = (v_proj > (h * 0.02)).astype(int)
    starts = np.sum(np.diff(ink_mask) == 1)

    if ink_mask[0] == 1:
        starts += 1

    real_cols = int(starts) if starts > 0 else config["cols"]

    # 3. Lectura de inyectores
    block_w = max(1, w // real_cols)
    injection_map = np.zeros((rows, real_cols))

    for c in range(real_cols):
        x1 = int(c * block_w)
        x2 = int((c + 1) * block_w)

        col_strip = thresh[:, x1:x2]
        h_proj = np.sum(col_strip, axis=1) / 255

        for r in range(rows):
            center_y = int((r / rows) * h)
            margin = max(1, int((h / rows) * 0.9))

            y1 = max(0, center_y - margin)
            y2 = min(h, center_y + margin)

            segmento = h_proj[y1:y2]

            if segmento.size > 0:
                if np.max(segmento) >= 1:
                    injection_map[r, c] = 1
            else:
                injection_map[r, c] = 0

    detectados = np.sum(injection_map)

    porcentaje = (
        (detectados / (rows * real_cols)) * 100
        if (rows * real_cols) > 0 else 0
    )

    return porcentaje, injection_map


# ===============================
# 🔵 STANDARD (VUTEK, DURST, etc.)
# ===============================
def process_smart_grid(cropped_image, config):
    if not isinstance(cropped_image, np.ndarray):
        cropped_image = np.array(cropped_image.convert("RGB"))
        cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_RGB2BGR)

    # 🎯 Pre-procesamiento
    gray = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)

    if config.get("use_blur", False):
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )
    gray_eq = clahe.apply(gray)

    sensibilidad = config.get("threshold_constant", 12)

    thresh = cv2.adaptiveThreshold(
        gray_eq,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        sensibilidad
    )

    if config.get("use_dilation", False):
        kernel = np.ones((2, 2), np.uint8)
        thresh = cv2.dilate(thresh, kernel, iterations=1)

    h, w = thresh.shape
    rows = config["rows"]
    cols = config["cols"]
    machine_type = config.get("type", "standard")

    # 📐 MOTOR
    thresh_float = thresh.astype(np.float32) / 255.0
    grid_density = cv2.resize(
        thresh_float,
        (cols, rows),
        interpolation=cv2.INTER_AREA
    )

    min_limit = config.get("pixel_min_limit", 0.23)

    if machine_type == "durst_block":
        injection_map = (grid_density >= min_limit).astype(int)
    else:
        injection_map = (grid_density >= min_limit).astype(int)

    # 🧠 ESPACIOS
    ignore_empty = config.get("ignore_empty_cols", False)

    if ignore_empty:
        col_activity = np.sum(grid_density, axis=0)
        active_cols = col_activity > 0.1

        for c in range(cols):
            if not active_cols[c]:
                injection_map[:, c] = 0
    else:
        active_cols = np.ones(cols, dtype=bool)

    # 📊 RESULTADO
    detectados = np.sum(injection_map)
    valid_cols = np.sum(active_cols)

    total_posible = (
        rows * valid_cols if valid_cols > 0 else (rows * cols)
    )

    porcentaje = (
        (detectados / total_posible) * 100
        if total_posible > 0 else 0
    )

    return porcentaje, injection_map


# ===============================
# 🚀 FUNCIÓN PRINCIPAL
# ===============================
def process_test_image_v2(image, machine_name):
    if not isinstance(image, np.ndarray):
        image = np.array(image.convert('RGB'))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if machine_name not in MACHINE_CONFIGS:
        raise ValueError(f"Máquina no configurada: {machine_name}")

    config = MACHINE_CONFIGS[machine_name]

    # 🔧 1. Alinear
    aligned = auto_align_image(image)

    # 🔍 2. ROI
    roi = detect_roi_auto(aligned)

    # 🎯 3. Procesar
    if config.get("type") == "epson":
        return process_epson_final(roi, config)
    else:
        return process_smart_grid(roi, config)





