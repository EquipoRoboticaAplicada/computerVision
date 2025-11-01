import cv2 as cv
import numpy as np

# --- Parámetros de detección ---
# Rangos HSV (ajústalos si cambian las condiciones de luz)
RANGES = {
    "Amarillo": (np.array([15, 120, 120]),  np.array([35, 255, 255])),
    "Azul":     (np.array([90, 120,  70]),  np.array([130,255, 255])),
    # Rojo requiere 2 rangos por el wrap de H (0/180)
    "Rojo1":    (np.array([0,  120, 120]),  np.array([10, 255, 255])),
    "Rojo2":    (np.array([170,120, 120]),  np.array([180,255, 255])),
}

# Colores para dibujar (BGR)
DRAW = {
    "Amarillo": (0, 255, 255),
    "Azul":     (255, 0, 0),
    "Rojo":     (0, 0, 255),
}

MIN_AREA = 600  # píxeles mínimos del contorno para considerarlo válido
KERNEL = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))

def process_mask(mask):
    """Limpia la máscara con apertura y cierre para reducir ruido y rellenar huecos."""
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN,  KERNEL, iterations=1)
    mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, KERNEL, iterations=1)
    return mask

def find_and_draw(mask, frame_draw, label, color_bgr):
    """Encuentra contornos en 'mask' y dibuja cajas + etiqueta en 'frame_draw'."""
    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv.contourArea(cnt) > MIN_AREA:
            x, y, w, h = cv.boundingRect(cnt)
            cv.rectangle(frame_draw, (x, y), (x+w, y+h), color_bgr, 2)
            cv.putText(frame_draw, label, (x, y-8), cv.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2, cv.LINE_AA)

# --- Captura ---
webcam = cv.VideoCapture(0)

while True:
    ret, frame = webcam.read()
    if not ret:
        break

    # (Opcional) voltear para efecto espejo:
    # frame = cv.flip(frame, 1)

    # Suavizado para reducir ruido antes de HSV
    blurred = cv.GaussianBlur(frame, (5, 5), 0)

    # BGR -> HSV
    hsv = cv.cvtColor(blurred, cv.COLOR_BGR2HSV)

    # --- Amarillo ---
    low, up = RANGES["Amarillo"]
    mask_y = cv.inRange(hsv, low, up)
    mask_y = process_mask(mask_y)
    find_and_draw(mask_y, frame, "Amarillo", DRAW["Amarillo"])

    # --- Azul ---
    low, up = RANGES["Azul"]
    mask_b = cv.inRange(hsv, low, up)
    mask_b = process_mask(mask_b)
    find_and_draw(mask_b, frame, "Azul", DRAW["Azul"])

    # --- Rojo (dos máscaras unidas) ---
    low1, up1 = RANGES["Rojo1"]
    low2, up2 = RANGES["Rojo2"]
    mask_r1 = cv.inRange(hsv, low1, up1)
    mask_r2 = cv.inRange(hsv, low2, up2)
    mask_r = cv.bitwise_or(mask_r1, mask_r2)
    mask_r = process_mask(mask_r)
    find_and_draw(mask_r, frame, "Rojo", DRAW["Rojo"])

    # Mostrar resultado
    cv.imshow('Detección de colores (d = salir)', frame)

    # Salir con 'd'
    if cv.waitKey(20) & 0xFF == ord('d'):
        break

webcam.release()
cv.destroyAllWindows()
