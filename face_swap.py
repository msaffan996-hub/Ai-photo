# face_swap.py
import cv2
import numpy as np
from PIL import Image
import face_recognition

def get_face_landmarks(img):
    # returns first face landmarks (dictionary)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = face_recognition.face_landmarks(img_rgb)
    return faces[0] if faces else None

def extract_face_mask_and_points(img, landmarks):
    # landmarks: dict with keys like 'chin','left_eye',...
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    # use chin and other points to form face polygon
    chin = landmarks.get('chin', [])
    left_eyebrow = landmarks.get('left_eyebrow', [])
    right_eyebrow = landmarks.get('right_eyebrow', [])
    jaw = chin
    poly = chin
    # create convex hull around relevant landmarks
    points = []
    for part in ['chin','left_eyebrow','right_eyebrow','nose_bridge','nose_tip','left_eye','right_eye','top_lip','bottom_lip']:
        pts = landmarks.get(part, [])
        points.extend(pts)
    if not points:
        return None, None
    points = np.array(points, dtype=np.int32)
    hull = cv2.convexHull(points)
    cv2.fillConvexPoly(mask, hull, 255)
    return mask, hull

def warp_face(src_img, src_landmarks, dst_img, dst_landmarks):
    # We'll compute affine transforms between corresponding points (eyes + nose)
    # Choose three anchor points: left_eye_center, right_eye_center, nose_tip
    def center_of(pts):
        arr = np.array(pts, dtype=np.int32)
        return np.mean(arr, axis=0).astype(np.int32)
    src_left = center_of(src_landmarks['left_eye'])
    src_right = center_of(src_landmarks['right_eye'])
    src_nose = np.array(src_landmarks['nose_tip'])[len(src_landmarks['nose_tip'])//2]
    dst_left = center_of(dst_landmarks['left_eye'])
    dst_right = center_of(dst_landmarks['right_eye'])
    dst_nose = np.array(dst_landmarks['nose_tip'])[len(dst_landmarks['nose_tip'])//2]

    src_pts = np.array([src_left, src_right, src_nose], dtype=np.float32)
    dst_pts = np.array([dst_left, dst_right, dst_nose], dtype=np.float32)

    M = cv2.getAffineTransform(src_pts, dst_pts)
    warped = cv2.warpAffine(src_img, M, (dst_img.shape[1], dst_img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return warped, M

def color_correct(src_face, dst_face, mask):
    # simple color correction: match mean in mask area for each channel
    src_masked = cv2.bitwise_and(src_face, src_face, mask=mask)
    dst_masked = cv2.bitwise_and(dst_face, dst_face, mask=mask)
    src_mean = [np.mean(src_masked[:,:,i][mask>0]) if np.any(mask>0) else 1 for i in range(3)]
    dst_mean = [np.mean(dst_masked[:,:,i][mask>0]) if np.any(mask>0) else 1 for i in range(3)]
    corrected = src_face.copy().astype(np.float32)
    for i in range(3):
        if src_mean[i] != 0:
            corrected[:,:,i] = corrected[:,:,i] * (dst_mean[i]/(src_mean[i]+1e-6))
    corrected = np.clip(corrected,0,255).astype(np.uint8)
    return corrected

def seamless_merge(warped_face, dst_img, mask):
    # find center for seamlessClone
    x,y,w,h = cv2.boundingRect(mask)
    center = (x + w//2, y + h//2)
    output = cv2.seamlessClone(warped_face, dst_img, mask, center, cv2.NORMAL_CLONE)
    return output

def merge_faces(source_image_path, target_image_path, result_path):
    src = cv2.imread(source_image_path)
    dst = cv2.imread(target_image_path)

    src_landmarks = get_face_landmarks(src)
    dst_landmarks = get_face_landmarks(dst)
    if src_landmarks is None or dst_landmarks is None:
        raise ValueError("No face detected in source or target")

    # get masks & hull for dst
    dst_mask, dst_hull = extract_face_mask_and_points(dst, dst_landmarks)
    if dst_mask is None:
        raise ValueError("Could not create mask for target")

    # warp source to target
    warped_src, M = warp_face(src, src_landmarks, dst, dst_landmarks)

    # create mask for warped face by transforming src mask
    src_mask, src_hull = extract_face_mask_and_points(src, src_landmarks)
    h,w = dst.shape[:2]
    warped_mask = cv2.warpAffine(src_mask, M, (w,h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    _, warped_mask = cv2.threshold(warped_mask, 10, 255, cv2.THRESH_BINARY)

    # color correct warped onto dst region
    corrected = color_correct(warped_src, dst, warped_mask)

    # final seamless cloning
    output = seamless_merge(corrected, dst, warped_mask)

    cv2.imwrite(result_path, output)
    return result_path
