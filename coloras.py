import cv2 as cv
import numpy as np

# --- Rangos HSV (puedes afinarlos según tu iluminación) ---
RANGES = {
    "Amarillo": (np.array([15, 120, 140]), np.array([35, 255, 255])),   # algo brillante
    "Azul":     (np.array([90, 120,  70]), np.array([130,255, 255])),
    # Rojo (dos rangos por el wrap)
    "Rojo1":    (np.array([0,  120, 120]), np.array([10, 255, 255])),
    "Rojo2":    (np.array([170,120, 120]), np.array([180,255, 255])),
    # Café (naranja oscuro: H similar a amarillo/naranja pero con V más baja)
    "Cafe":     (np.array([5,  120,  20]), np.array([25, 255, 160]))
    #            H: 5–25  | S: >=120   | V: <=160 (oscuro). Sube/baja V para afinar.
}

# Colores para dibujar (BGR)
DRAW = {
    "Amarillo": (0, 255, 255),
    "Azul":     (255, 0, 0),
    "Rojo":     (0, 0, 255),
    "Cafe":     (19, 69, 139),  # marrón oscuro aproximado
}

MIN_AREA = 600
KERNEL = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))

def process_mask(mask):
    # Limpieza morfológica: quita ruido y rellena huecos
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN,  KERNEL, iterations=1)
    mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, KERNEL, iterations=1)
    return mask

def find_and_draw(mask, frame_draw, label, color_bgr):
    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv.contourArea(cnt) > MIN_AREA:
            x, y, w, h = cv.boundingRect(cnt)
            cv.rectangle(frame_draw, (x, y), (x+w, y+h), color_bgr, 2)
            cv.putText(frame_draw, label, (x, y-8), cv.FONT_HERSHEY_SIMPLEX, 0.7, color_bgr, 2, cv.LINE_AA)

webcam = cv.VideoCapture(0)

while True:
    ret, frame = webcam.read()
    if not ret:
        break

    # Opcional: efecto espejo
    # frame = cv.flip(frame, 1)

    # Suavizado previo
    blurred = cv.GaussianBlur(frame, (5, 5), 0)
    hsv = cv.cvtColor(blurred, cv.COLOR_BGR2HSV)

    # --- Café primero (para restarlo del amarillo y evitar solapamientos) ---
    lowC, upC = RANGES["Cafe"]
    mask_cafe = cv.inRange(hsv, lowC, upC)
    mask_cafe = process_mask(mask_cafe)
    find_and_draw(mask_cafe, frame, "Café", DRAW["Cafe"])

    # --- Amarillo (restamos café para no etiquetar lo mismo dos veces) ---
    lowY, upY = RANGES["Amarillo"]
    mask_y = cv.inRange(hsv, lowY, upY)
    mask_y = cv.bitwise_and(mask_y, cv.bitwise_not(mask_cafe))  # quita zonas oscuras café
    mask_y = process_mask(mask_y)
    find_and_draw(mask_y, frame, "Amarillo", DRAW["Amarillo"])

    # --- Azul ---
    lowB, upB = RANGES["Azul"]
    mask_b = cv.inRange(hsv, lowB, upB)
    mask_b = process_mask(mask_b)
    find_and_draw(mask_b, frame, "Azul", DRAW["Azul"])

    # --- Rojo (dos máscaras unidas) ---
    lowR1, upR1 = RANGES["Rojo1"]
    lowR2, upR2 = RANGES["Rojo2"]
    mask_r1 = cv.inRange(hsv, lowR1, upR1)
    mask_r2 = cv.inRange(hsv, lowR2, upR2)
    mask_r = cv.bitwise_or(mask_r1, mask_r2)
    mask_r = process_mask(mask_r)
    find_and_draw(mask_r, frame, "Rojo", DRAW["Rojo"])

    cv.imshow('Detección de colores (d = salir)', frame)
    if cv.waitKey(20) & 0xFF == ord('d'):
        break

webcam.release()
cv.destroyAllWindows()
