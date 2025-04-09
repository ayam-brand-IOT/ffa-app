import cv2
import numpy as np
import math
import json
import time

cap = cv2.VideoCapture(0)

__RATIO__ = 16/9
__CAMERA_WIDTH__ = 550
__CAMERA_HEIGTH__ = math.floor(__CAMERA_WIDTH__/__RATIO__)
__FRAMESIZE__ = (1000, 650)
__MAIN_PATH__ ="./muestras/opencv_frame_" # path to save images

__CONFIG_PATH__ = "./vision_config.json"

last_frame = None
captured_data = None
frameReadyCallback = None

coef_calibration = 0.23 #0.19*1.22
zoi_x1 = 40
zoi_y1 = 100
zoi_x2 = 500
zoi_y2 = 500
Z1 = 40  # Size of the tail we want

# Parámetros de pescado (estos se actualizarán según la selección)
fish_parameters = {
    "A": None,
    "B": None,
    "C": None
}

def loadConfig():
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        global zoi_x1, zoi_y1, zoi_x2, zoi_y2, coef_calibration, Z1
        zoi_x1, zoi_y1 = math.floor(config['zoi'][0]['x']), math.floor(config['zoi'][0]['y'])
        zoi_x2, zoi_y2 = math.floor(config['zoi'][1]['x']), math.floor(config['zoi'][1]['y'])
        coef_calibration = config['ppmm']
        Z1 = math.floor(config['tailTrigger'])
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")
    

loadConfig()

# Función para actualizar los parámetros de pescado.
def update_fish_parameters(params):
    """
    Actualiza la variable global fish_parameters con los valores nuevos.
    Además, persiste estos valores en vision_config.json bajo la clave "current_fish_params"
    si se desea (opcional).
    """
    global fish_parameters
    fish_parameters = params
    print("Fish parameters updated:", fish_parameters)
    # (Opcional) Actualizar el archivo de configuración:
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
    except Exception as e:
        print("Error al leer vision_config.json:", e)
        config = {}
    # Puedes elegir guardar estos parámetros en una nueva clave para referencia,
    # por ejemplo, "current_fish_params"
    config["current_fish_params"] = params
    try:
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print("Error al escribir los fish parameters en vision_config.json:", e)

captured = False
# pause_image = False
ZOI_start = [zoi_x1, zoi_y1]
ZOI_end = [zoi_x2, zoi_y2]
lytho = 1.2  # user threshold 1.2
img_counter = 0
zero_line = 200
offset = 10

def write_px_mm_ratio(ratio):
    global coef_calibration
    coef_calibration = ratio
    print("set ratio: ", ratio)
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        config['ppmm'] = ratio
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print(f"Error writting px/mm: {e}")

def writeZOI(points):
    global zoi_x1, zoi_y1, zoi_x2, zoi_y2
    zoi_x1, zoi_y1 = math.floor(points[0]['x']), math.floor(points[0]['y'])
    zoi_x2, zoi_y2 = math.floor(points[1]['x']), math.floor(points[1]['y'])
    print("set zoi: ", points)
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        config['zoi'] = points
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print(f"Error writting ZOI: {e}")

def handle_capture(callback):
    global captured, frameReadyCallback
    print("capture")
    frameReadyCallback = callback
    captured = True

def getAnalyzedImage():
    return last_frame
    
def get_analysis_data():
    global captured_data
    return captured_data

def handle_reset():
    global captured, captured_data
    captured = False
    # pause_image = False
    captured_data = None
    print("reset")

# def updateImage():
#     global captured, img_counter, cap, last_frame, zoi_x1, captured_data, frameReadyCallback
#     if captured:
#         # ios.flash(True)
#         # ios.laser(False)
#         # time.sleep(10.5)
#         print("Capturing image")

#         ret, frame = cap.read()
#         frame = cv2.resize(frame, (1000, 650))

#         img_name = __MAIN_PATH__+"{}.png".format(img_counter)
#         cv2.imwrite(img_name, frame)
#         print("{} written!".format(img_name))
#         # im = cv2.imread( __MAIN_PATH__+ str(img_counter) + ".png")
#         im = frame
#         img_counter += 1

#         img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
#         blur = cv2.GaussianBlur(img, (13, 13), 0)
#         ret3, th3 = cv2.threshold(blur, 0, 1, cv2.THRESH_OTSU)  # cv.THRESH_BINARY
#         ret4, BW = cv2.threshold(blur, ret3 * lytho, 1, cv2.THRESH_BINARY)

#         # Task 1b : Determine when to start ZOI
#         # 1st one for fish with head
#         diameter_full_image = []
#         for j in range(BW.shape[1]):  # shape[0] = on the height (y-axis) and shape[1] on the width (x-axis)
#             d = np.sum(1 - BW[:, j])  # sum all the '0' pixel on the Y (ROIBW[x,y])
#             diameter_full_image.append(d) # the tab diameter have all the diameter of the fish for each x0...xn
#         Df = np.max(diameter_full_image) # search what is the max on the tab diameter

#             # 2nd one for fish without head with a block
#         Dfindex = diameter_full_image.index(Df)
#         for j in range(Dfindex,len(diameter_full_image)-Dfindex): # We start from the biggest black line until the end of thet tab
#             if diameter_full_image[j] < Df: # Once we have something less than the biggest one it means that it's finished
#                 break
#         zoi = j

#         ### Task 2 : Zone Of Interest (ZOI) a.k.a Zone of Measurement
#         ROIBW = BW[zoi_y1:zoi_y2, zero_line:zoi_x2]  # source_image[ start_row : end_row, start_col : end_col] row = y, column = x
#         cv2.rectangle(im, (zoi_x1, zoi_y1), (zoi_x2, zoi_y2), (0, 255, 0), 1)
#         cv2.putText(im,"Zone Of Interest",(zoi_x2-150, zoi_y2+30),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,150,0),1)
#         cv2.line(im,(zero_line, zoi_y1),(zero_line, zoi_y2),(0,0,255),1)
        
#         # Print zero line
#         cv2.line(im,(zero_line + offset, zoi_y1),(zero_line + offset, zoi_y2),(0,255,0),1)

#         ###Task 2 : Region of Interest (ROI)
#         # y1 = 60
#         # x2 = 950
#         # x1 = 215
#         # # if zoi > x2:
#         # #     x1 = 50
#         # # else:
#         # #     x1 = zoi+4
#         # y2 = 600
#         # ROIBW = BW[y1:y2, x1:x2]  # source_image[ start_row : end_row, start_col : end_col] row = y, column = x
#         # cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 0), 1)
#         # cv2.putText(im,"Zone Of Interest",(x2-150, y2+30),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,200,0),1)

#         ###Task 3 : Size of the fish from zero line to tail
#         diameter = []
#         for j in range(ROIBW.shape[1]):  # shape[0] = on the height (y-axis) and shape[1] on the width (x-axis)
#             w = np.sum(1 - ROIBW[:, j])  # sum all the '0' pixel on the Y (ROIBW[x,y])
#             diameter.append(w) # the tab diameter have all the diameter of the fish for each x0...xn

#             if w <= Z1: # stop the loop when the size of the diameter of the tail is reached
#                 break
#         L1 = j - offset
#         L1hgt = j
#         print('L1 is: ' + str(L1))

#         cv2.line(im,(L1hgt + zero_line, zoi_y1),(L1hgt + zero_line, zoi_y2),(255,0,0),1)
#         cv2.arrowedLine(im,(zero_line + offset, zoi_y1+20),(L1hgt+zero_line, zoi_y1+20),(0,0,255),2,1,0,0.03) 
#         cv2.arrowedLine(im,(L1hgt+zero_line, zoi_y1+20),(zero_line+offset, zoi_y1+20),(0,0,255),2,1,0,0.03)
#         cv2.putText(im,"L1 : " +str(round(L1*coef_calibration,1))+str(" mm"),(L1+zero_line+20, zoi_y1+30),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
#         # cv2.putText(im,"L1hgt : " +str(round(L1hgt*coef_calibration,1))+str(" mm"),(L1hgt+zero_line+20, zoi_y1+60),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
        
#         ####Task 4 : Surface of the fish
#         S1 = np.sum(np.sum(1 - ROIBW[:, 1:L1]))
#         print('Black area is: ' + str(S1))

#         ###Task 5 : Biggest diameter of the fish
#         D1 = np.max(diameter) # search what is the max on the tab diameter
#         D1index = diameter.index(D1)
#         c = (1 - ROIBW[:, D1index])  # c is all the points on y-axis at the D1index point on the x-axis

#         for i in range(len(c)):
#             if c[i] == 1:
#                 cv2.circle(im, (zero_line + D1index, i+zoi_y1), 1, (200, 0, 255), 1) # we add circle each time there is a 1 so we can display the diameter

#         print('D1 is: ' + str(D1))

#         cv2.putText(im,"D1 : " +str(round(D1*coef_calibration,1))+str(" mm"),(D1index+zero_line+20, zoi_y1+250),cv2.FONT_HERSHEY_SIMPLEX,1,(200,0,255),3)

#         ###Task 6 : Size of the head
#         ROIBW_HEAD = BW[zoi_y1:zoi_y2, zoi_x1:zoi_x2]  # source_image[ start_row : end_row, start_col : end_col] row = y, column = x
#         for j in range(ROIBW_HEAD.shape[1]):
#             w2 = np.sum(1 - ROIBW_HEAD[:, j])
#             if w2 > 2:
#                 break
#         L2 = zero_line - j - zoi_x1
#         print('L2 is: ' + str(L2))

#         cv2.line(im,(zero_line - L2, zoi_y1),(zero_line - L2, zoi_y2),(255,0,0),1)
#         cv2.arrowedLine(im,(zero_line + offset, zoi_y2),(zero_line - L2, zoi_y2),(0,0,255),2,1,0,0.04) 
#         cv2.arrowedLine(im,(zero_line -L2, zoi_y2),(zero_line + offset, zoi_y2),(0,0,255),2,1,0,0.04)
#         cv2.putText(im,"L2 : " +str(abs(round(L2*coef_calibration,1)))+str(" mm"),(L2+zero_line+20, zoi_y2+40),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
#         # self.updateImage(im)
#         last_frame = im
#         if captured_data == None:
#             captured_data = '{ "length": '+str(round(L1*coef_calibration,1))+', "height": '+str(round(D1*coef_calibration,1))+', "head": '+str(abs(round(L2*coef_calibration,1)))+', "tail_trigger": '+str(round(Z1*coef_calibration,1))+' }'
        
#         captured = False
#         frameReadyCallback()
#         # return im 
#         return frame
        

#     elif not captured:

#         ret, frame = cap.read()
#         frame = cv2.resize(frame, (1000, 650))
#     #  cap.release()
#     # if captured and not pause_image:
        
#         # self.updateImage(frame)
#         return frame
    
#     # else:
#     #     # self.updateImage(last_frame)
#     #     return last_frame


def updateImage():
    global captured, img_counter, cap, last_frame, zoi_x1, captured_data, frameReadyCallback, zero_line
    if captured:
        print("Capturing image")

        # Verificar si la imagen se capturó correctamente
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen de la cámara")
            return

        frame = cv2.resize(frame, (1000, 650))

        img_name = __MAIN_PATH__+"{}.png".format(img_counter)
        cv2.imwrite(img_name, frame)
        print("{} written!".format(img_name))

        im = frame
        img_counter += 1

        img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(img, (13, 13), 0)
        ret3, th3 = cv2.threshold(blur, 0, 1, cv2.THRESH_OTSU)
        ret4, BW = cv2.threshold(blur, ret3 * lytho, 1, cv2.THRESH_BINARY)

        # Verificar dimensiones de la imagen
        height, width = BW.shape
        print(f"Dimensiones de BW: {BW.shape}")

        # Asegurarse de que zero_line < zoi_x2
        if zero_line >= zoi_x2:
            print(f"Ajustando zero_line de {zero_line} a {zoi_x1}")
            zero_line = zoi_x1

        # Clipping de índices para estar dentro de los límites de la imagen
        zoi_y1_clipped = max(0, min(zoi_y1, height))
        zoi_y2_clipped = max(0, min(zoi_y2, height))
        zero_line_clipped = max(0, min(zero_line, width))
        zoi_x2_clipped = max(0, min(zoi_x2, width))

        # Definir la Zona de Interés (ZOI)
        ROIBW = BW[zoi_y1_clipped:zoi_y2_clipped, zero_line_clipped:zoi_x2_clipped]

        # Verificar si ROIBW tiene dimensiones válidas
        if ROIBW.size == 0 or ROIBW.shape[1] == 0:
            print("ROIBW tiene dimensiones inválidas. Verifique los valores de zoi_y1, zoi_y2, zero_line y zoi_x2.")
            return

        print(f"ROIBW shape: {ROIBW.shape}")

        cv2.rectangle(im, (zoi_x1, zoi_y1), (zoi_x2, zoi_y2), (0, 255, 0), 1)
        cv2.putText(im, "Zone Of Interest", (zoi_x2-150, zoi_y2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,150,0), 1)
        cv2.line(im, (zero_line, zoi_y1), (zero_line, zoi_y2), (0,0,255), 1)
        cv2.line(im, (zero_line + offset, zoi_y1), (zero_line + offset, zoi_y2), (0,255,0), 1)

        # Calcular el diámetro
        diameter = []
        for j in range(ROIBW.shape[1]):
            w = np.sum(1 - ROIBW[:, j])
            diameter.append(w)
            if w <= Z1:
                break

        # Verificar que la lista 'diameter' no esté vacía
        if len(diameter) == 0:
            print("La lista 'diameter' está vacía, no se puede calcular el máximo. Verifique los valores de ROIBW.")
            return

        L1 = j - offset
        L1hgt = j
        print('L1 is: ' + str(L1))

        cv2.line(im, (L1hgt + zero_line, zoi_y1), (L1hgt + zero_line, zoi_y2), (255,0,0), 1)
        cv2.arrowedLine(im, (zero_line + offset, zoi_y1+20), (L1hgt+zero_line, zoi_y1+20), (0,0,255), 2, 1, 0, 0.03)
        cv2.arrowedLine(im, (L1hgt+zero_line, zoi_y1+20), (zero_line+offset, zoi_y1+20), (0,0,255), 2, 1, 0, 0.03)
        cv2.putText(im, "L1 : " + str(round(L1*coef_calibration,1)) + " mm", (L1+zero_line+20, zoi_y1+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)

        # Calcular el área negra
        S1 = np.sum(np.sum(1 - ROIBW[:, 1:L1]))
        print('Black area is: ' + str(S1))

        # Calcular el diámetro máximo
        D1 = np.max(diameter)
        D1index = diameter.index(D1)
        c = (1 - ROIBW[:, D1index])

        for i in range(len(c)):
            if c[i] == 1:
                cv2.circle(im, (zero_line + D1index, i+zoi_y1), 1, (200, 0, 255), 1)

        print('D1 is: ' + str(D1))

        cv2.putText(im, "D1 : " + str(round(D1*coef_calibration,1)) + " mm", (D1index+zero_line+20, zoi_y1+250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200,0,255), 3)

        # Ajuste de índices para la cabeza
        zoi_x1_clipped = max(0, min(zoi_x1, width))
        zoi_x2_clipped = max(0, min(zoi_x2, width))
        ROIBW_HEAD = BW[zoi_y1_clipped:zoi_y2_clipped, zoi_x1_clipped:zero_line_clipped]

        # Verificar si ROIBW_HEAD tiene dimensiones válidas
        if ROIBW_HEAD.size == 0 or ROIBW_HEAD.shape[1] == 0:
            print("ROIBW_HEAD tiene dimensiones inválidas. Verifique los valores de zoi_x1 y zero_line.")
            return

        # Calcular el tamaño de la cabeza
        for j in range(ROIBW_HEAD.shape[1]):
            w2 = np.sum(1 - ROIBW_HEAD[:, j])
            if w2 > 2:
                break
        L2 = zero_line - j - zoi_x1
        print('L2 is: ' + str(L2))

        cv2.line(im, (zero_line - L2, zoi_y1), (zero_line - L2, zoi_y2), (255,0,0), 1)
        cv2.arrowedLine(im, (zero_line + offset, zoi_y2), (zero_line - L2, zoi_y2), (0,0,255), 2, 1, 0, 0.04)
        cv2.arrowedLine(im, (zero_line - L2, zoi_y2), (zero_line + offset, zoi_y2), (0,0,255), 2, 1, 0, 0.04)
        cv2.putText(im, "L2 : " + str(abs(round(L2*coef_calibration,1))) + " mm", (L2+zero_line+20, zoi_y2+40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)

        last_frame = im
        if captured_data == None:
            captured_data = '{ "length": '+str(round(L1*coef_calibration,1))+', "height": '+str(round(D1*coef_calibration,1))+', "head": '+str(abs(round(L2*coef_calibration,1)))+', "tail_trigger": '+str(round(Z1*coef_calibration,1))+' }'

        captured = False
        frameReadyCallback()
        return frame

    elif not captured:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar la imagen de la cámara")
            return
        frame = cv2.resize(frame, (1000, 650))
        return frame
