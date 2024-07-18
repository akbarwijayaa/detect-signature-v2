import cv2
import matplotlib.pyplot as plt
from skimage import measure, morphology
from skimage.measure import regionprops
import numpy as np
from flask import current_app, jsonify
import os

class SignatureController:
    def __init__(self) -> None:
        self.constant_parameter_1 = 72
        self.constant_parameter_2 = 250
        self.constant_parameter_3 = 110
        self.constant_parameter_4 = 18
    
    def crop_image(self, img, filename, mode):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 6)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.imwrite(os.path.join(current_app.config['UPLOAD_FOLDER'], 'cropped', 'test'), contours)
        
        x_list = []

        for idx, cnt in enumerate(contours):
            approx = cv2.approxPolyDP(cnt, 0.01*cv2.arcLength(cnt, True), True)
            if len(approx) > 3 and len(approx) < 1000:
                x, y, w, h = cv2.boundingRect(cnt)
                ratio = float(w) / h
                if ratio <= 0.9 or ratio >= 1.1:
                    if w > 120 and w < 300 and y > 500 and h > 130 and h < 300:
                        x_list.append({"idx": idx, "x": x, "y": y, "w": w, "h": h})

        if len(x_list) <= 1:
            return []

        x_list = sorted(x_list, key=lambda o: o['x'])

        mode_mapping = {
            "PENERIMA": 0,
            "PENGIRIM": 1,
            "PENGELUARAN": 2,
            "GUDANG": 3,
            "PEMASARAN_MENGETAHUI": -2,
            "PEMASARAN_TGL": -1
        }

        if len(x_list) < 6 and mode == "PENGELUARAN":
            return []

        idx = mode_mapping[mode]
        if idx < 0:
            cnt_index = x_list[idx]['idx'] if abs(idx) <= len(x_list) else -1
        else:
            cnt_index = x_list[idx]['idx'] if idx < len(x_list) else -1

        if cnt_index < 0:
            return []

        x, y, w, h = cv2.boundingRect(contours[cnt_index])
        img = cv2.drawContours(img, [contours[cnt_index]], -1, (0, 255, 0), 3)
        img = thresh[y:y + h - 5, x:x + w - 5]

        cv2.imwrite(os.path.join(current_app.config['UPLOAD_FOLDER'], 'cropped', filename), img)
        return img

    def remove_file(self, filename):
        if current_app.debug:
            pass
        raw = os.path.join(current_app.config['UPLOAD_FOLDER'], 'raw', filename)
        if os.path.exists(raw):
            os.remove(raw)

        cropped = os.path.join(current_app.config['UPLOAD_FOLDER'], 'cropped', filename)
        if os.path.exists(cropped):
            os.remove(cropped)

        preversion = os.path.join(current_app.config['UPLOAD_FOLDER'], 'preversion', filename)
        if os.path.exists(preversion):
            os.remove(preversion)

    def detect_signature(self, file, filename, mode):
        img = cv2.imread(file)
        
        # Rotate image and attempt detection
        detected_img = self.try_detect_signature(img, filename, mode)
        if detected_img is not None:
            return detected_img
        
        # Try 90 degrees rotation
        img_rotated_90 = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        detected_img = self.try_detect_signature(img_rotated_90, filename, mode)
        if detected_img is not None:
            return detected_img
        
        # Try 180 degrees rotation
        img_rotated_180 = cv2.rotate(img, cv2.ROTATE_180)
        detected_img = self.try_detect_signature(img_rotated_180, filename, mode)
        if detected_img is not None:
            return detected_img
        
        # Try 270 degrees rotation
        img_rotated_270 = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        detected_img = self.try_detect_signature(img_rotated_270, filename, mode)
        if detected_img is not None:
            return detected_img
        
        self.remove_file(filename)
        return jsonify(message="Tidak berhasil mendeteksi tanda tangan. Pastikan gambar dalam posisi sesuai!"), 400
    
    def try_detect_signature(self, img, filename, mode):
        img = self.crop_image(img, filename, mode)

        if len(img) <= 0:
            return None

        blobs = img > img.mean()
        blobs_labels = measure.label(blobs, background=1)

        the_biggest_component = 0
        total_area = 0
        counter = 0
        for region in regionprops(blobs_labels):
            if region.area > 10:
                total_area += region.area
                counter += 1
            if region.area >= 250 and region.area > the_biggest_component:
                the_biggest_component = region.area

        average = total_area / counter if counter > 0 else 0
        a4_small_size_outliar_constant = ((average / self.constant_parameter_1) * self.constant_parameter_2) + self.constant_parameter_3
        a4_big_size_outliar_constant = a4_small_size_outliar_constant * self.constant_parameter_4

        pre_version = morphology.remove_small_objects(blobs_labels, a4_small_size_outliar_constant)
        component_sizes = np.bincount(pre_version.ravel())
        too_small = component_sizes > a4_big_size_outliar_constant
        too_small_mask = too_small[pre_version]
        pre_version[too_small_mask] = 0

        plt.imsave(os.path.join(current_app.config['UPLOAD_FOLDER'], 'preversion', filename), pre_version)
        img = cv2.imread(os.path.join(current_app.config['UPLOAD_FOLDER'], 'preversion', filename), 0)
        img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        n_white_pix = int(np.sum(img == 255))
        is_signed = n_white_pix > 0
        data = {"is_signed": is_signed}
        message = "Tanda tangan terdeteksi" if is_signed else "Tanda tangan tidak terdeteksi"
        #self.remove_file(filename)

        return jsonify(data=data, message=message)
