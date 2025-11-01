#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import glob
import cv2 as cv
import numpy as np
import serial

# =========================
#  Utilidades de Serial
# =========================
def auto_serial_port():
    """
    Intenta localizar el puerto del Arduino automáticamente.
    Prioriza /dev/serial/by-id/ (estable), luego /dev/ttyACM* y /dev/ttyUSB*.
    """
    candidates = sorted(glob.glob("/dev/serial/by-id/*")) \
               + sorted(glob.glob("/dev/ttyACM*")) \
               + sorted(glob.glob("/dev/ttyUSB*"))
    return candidates[0] if candidates else None

def open_serial(baud=115200):
    port = auto_serial_port()
    if not port:
        print("⚠️  No se encontró Arduino por USB. Conéctalo y vuelve a ejecutar.")
        return None
    print(f"🔌 Conectando a Arduino en: {port}")
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=0, write_timeout=0)
        time.sleep(2.0)  # tiempo para que el Arduino reinicie el puerto
        return ser
    except Exception as e:
        print(f"❌ Error abriendo {port}: {e}")
        return None

def send_cmd(ser, text):
    """Envía una línea terminada en \\n, ignorando errores transitorios."""
    if ser is None:
        return
    try:
        ser.write((text + "\n").encode("ascii"))
    except Exception:
        pass

# =========================
#  Parámetros de visión
# =========================
# Rangos HSV (ajusta S/V según tu luz). Rojo usa 2 rangos por el wrap de H.
RANGES = {
    "Amarillo": (np.array([15, 120, 140]), np.array([35, 255, 255])),
    "Azul":     (np.array([90, 120,  70]), np.array([130,255,255])),
    "Rojo1":    (np.array([0,  120, 120]), np.array([10, 255, 255])),
    "Rojo2":    (np.array([170,120, 120]), np.array([180,255,255])),
    # Café opcional para visualizar (NO enciende motor):
    "Cafe":     (np.array([5,  120,  20]), np.array([25, 255, 160])),
}

# Colores de dibujo BGR
DRAW = {
    "Amarillo": (0, 255, 255),
    "Azul":     (255, 0, 0),
    "Rojo":     (0, 0, 255),
    "Cafe":     (19, 69, 139),
}

MIN_AREA = 800
KERNEL = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
KEEPALIVE_MS = 500  # enviar comando cada 0.5 s si el motor está ON (Arduino timeout=2 s)
SHOW_CAFE = True    # mostrar café en pantalla pero NO activa motor

def process_mask(mask):
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN,  KERNEL, iterations=1)
    mask = cv.morphologyEx(mask, cv.MORPH_CLOSE, KERNEL, iterations=1)
    return mask

def biggest_blob_area(mask):
    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    areas = [cv.contourArea(c) for c in contours]
    return (max(areas), contours[areas.index(max(areas))]) if areas else (0, None)

# =========================
#  Main
# =========================
def main():
    ser = open_serial(115200)

    cap = cv.VideoCapture(0)  # Usa la webcam USB
    if not cap.isOpened():
        print("❌ No se pudo abrir la cámara 0.")
        return

    last_cmd = "S"
    last_tx  = 0.0

    print("🎥 Detección activa. Presiona 'd' o 'q' para salir.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue

            # Opcional: espejo
            # frame = cv.flip(frame, 1)

            blurred = cv.GaussianBlur(frame, (5, 5), 0)
            hsv = cv.cvtColor(blurred, cv.COLOR_BGR2HSV)

            # --- Máscaras por color ---
            # Amarillo
            mask_y = cv.inRange(hsv, *RANGES["Amarillo"])
            mask_y = process_mask(mask_y)
            area_y, cnt_y = biggest_blob_area(mask_y)

            # Azul
            mask_b = cv.inRange(hsv, *RANGES["Azul"])
            mask_b = process_mask(mask_b)
            area_b, cnt_b = biggest_blob_area(mask_b)

            # Rojo (dos rangos)
            mask_r1 = cv.inRange(hsv, *RANGES["Rojo1"])
            mask_r2 = cv.inRange(hsv, *RANGES["Rojo2"])
            mask_r  = cv.bitwise_or(mask_r1, mask_r2)
            mask_r  = process_mask(mask_r)
            area_r, cnt_r = biggest_blob_area(mask_r)

            # Café (solo display)
            if SHOW_CAFE:
                mask_c = cv.inRange(hsv, *RANGES["Cafe"])
                mask_c = process_mask(mask_c)
                area_c, cnt_c = biggest_blob_area(mask_c)
            else:
                area_c, cnt_c = 0, None

            # --- Dibujar rectángulos/etiquetas ---
            def draw_cnt(cnt, label, color):
                if cnt is not None:
                    x,y,w,h = cv.boundingRect(cnt)
                    cv.rectangle(frame, (x,y), (x+w,y+h), color, 2)
                    cv.putText(frame, f"{label}", (x, y-8),
                               cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv.LINE_AA)

            if cnt_y is not None: draw_cnt(cnt_y, "Amarillo", DRAW["Amarillo"])
            if cnt_b is not None: draw_cnt(cnt_b, "Azul",     DRAW["Azul"])
            if cnt_r is not None: draw_cnt(cnt_r, "Rojo",     DRAW["Rojo"])
            if cnt_c is not None and SHOW_CAFE: draw_cnt(cnt_c, "Café", DRAW["Cafe"])

            # --- Lógica de control (elige el color con MAYOR área entre Y/R/B) ---
            chosen = None
            areas = [("Y", area_y, cnt_y), ("R", area_r, cnt_r), ("B", area_b, cnt_b)]
            areas = [(k,a,c) for (k,a,c) in areas if a >= MIN_AREA and c is not None]
            if areas:
                # mayor área
                areas.sort(key=lambda t: t[1], reverse=True)
                chosen = areas[0][0]  # 'Y', 'R' o 'B'

            # Determina comando actual
            curr_cmd = chosen if chosen is not None else "S"

            # Envío: solo en cambio o como keep-alive cada 0.5 s si ON
            now = time.time()
            need_keepalive = (curr_cmd in ("Y","R","B")) and ((now - last_tx) * 1000.0 >= KEEPALIVE_MS)
            if curr_cmd != last_cmd or need_keepalive:
                send_cmd(ser, curr_cmd)
                last_tx = now
                last_cmd = curr_cmd

            # Overlay de estado
            txt = f"CMD: {curr_cmd}  | Areas px2 -> Y:{int(area_y)} R:{int(area_r)} B:{int(area_b)}"
            cv.putText(frame, txt, (10, 24), cv.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv.LINE_AA)

            cv.imshow("Detección colores -> Arduino (d/q para salir)", frame)
            k = cv.waitKey(1) & 0xFF
            if k in (ord('d'), ord('q')):
                break

    finally:
        # apaga el motor al salir
        send_cmd(ser, "S")
        if ser:
            try: ser.close()
            except: pass
        cap.release()
        cv.destroyAllWindows()

if __name__ == "__main__":
    main()
