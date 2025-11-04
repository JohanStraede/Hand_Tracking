"""
Simple, minimal hand tracking using MediaPipe + OpenCV.

Features:
- Webcam capture (index 0)
- Hand detection and 21 keypoint landmarks
- Drawing landmarks and connections
- Simple per-hand finger counting
	- Thumb: counts as extended only when splayed to the side of the hand
		(uses palm lateral axis + depth gating to avoid 'in-front-of-palm' false positives)
	- Fingers (index/middle/ring/pinky): tip above PIP joint

Controls:
- Press 'q' to quit

Dependencies: opencv-python, mediapipe, numpy
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Sequence, Any, cast


# Import specific MediaPipe solution modules to satisfy type checkers
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import drawing_styles as mp_styles


def count_fingers(landmarks: Sequence, handedness_label: str) -> int:
	"""Count extended fingers using landmark geometry.

	Heuristic:
	- Thumb: considered extended only when splayed sideways (large lateral offset relative to palm width)
			 and not significantly protruding toward the camera (depth gate).
	- Index/Middle/Ring/Pinky: Tip y above (smaller than) PIP y => extended (image origin top-left).

	Args:
		landmarks: Sequence of 21 normalized landmarks with x,y,z in [0..1] (z negative toward camera).
		handedness_label: "Left" or "Right" (not strictly needed for this heuristic but kept for API symmetry).

	Returns:
		Number of extended fingers in [0..5].
	"""
	if len(landmarks) != 21:
		return 0

	# Convert to numpy for convenience
	pts2 = np.array([(lm.x, lm.y) for lm in landmarks], dtype=np.float32)  # (21,2)
	pts3 = np.array([(lm.x, lm.y, lm.z) for lm in landmarks], dtype=np.float32)  # (21,3)

	# Indices per MediaPipe Hands
	TIP_IDS = [4, 8, 12, 16, 20]
	PIP_IDS = [3, 6, 10, 14, 18]  # For thumb we use 3 (IP), others PIP

	fingers = []

	# Thumb detection (sideways extension):
	# Define palm lateral axis as vector from index MCP (5) to pinky MCP (17)
	index_mcp = pts3[5]
	pinky_mcp = pts3[17]
	palm_center = (pts3[5] + pts3[9] + pts3[13] + pts3[17]) / 4.0
	lateral_axis = pinky_mcp - index_mcp
	lw = np.linalg.norm(lateral_axis)
	if lw < 1e-6:
		# Fallback: small palm width -> use x-axis in image coords
		lateral_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
		lw = 1.0
	else:
		lateral_axis = lateral_axis / lw

	thumb_tip = pts3[4]
	lateral_offset = float(np.dot(thumb_tip - palm_center, lateral_axis))
	lateral_norm = lateral_offset / (lw + 1e-6)

	# Depth gate: if thumb is far towards camera relative to palm plane, likely in-front pose
	z_diff = float(thumb_tip[2] - palm_center[2])  # negative => tip closer to camera

	# Thresholds tuned for normalized coordinates; adjust if needed
	LATERAL_THRESH = 0.50  # how far to the side relative to palm width
	DEPTH_GATE = -0.05     # allow small forwards motion, but not large in-front

	thumb_extended = (abs(lateral_norm) > LATERAL_THRESH) and (z_diff > DEPTH_GATE)
	fingers.append(int(thumb_extended))

	# Index, Middle, Ring, Pinky: vertical check (tip above PIP)
	for tip_id, pip_id in zip(TIP_IDS[1:], PIP_IDS[1:]):
		tip_y = pts2[tip_id, 1]
		pip_y = pts2[pip_id, 1]
		fingers.append(int(tip_y < pip_y))

	return int(np.sum(fingers))


def finger_states(landmarks: Sequence) -> dict:
	"""Return per-finger extended state using the same heuristics as count_fingers.

	Returns a dict with boolean entries for keys: thumb, index, middle, ring, pinky.
	"""
	if len(landmarks) != 21:
		return {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}

	pts2 = np.array([(lm.x, lm.y) for lm in landmarks], dtype=np.float32)
	pts3 = np.array([(lm.x, lm.y, lm.z) for lm in landmarks], dtype=np.float32)

	# Palm lateral axis and center
	index_mcp = pts3[5]
	pinky_mcp = pts3[17]
	palm_center = (pts3[5] + pts3[9] + pts3[13] + pts3[17]) / 4.0
	lateral_axis = pinky_mcp - index_mcp
	lw = np.linalg.norm(lateral_axis)
	if lw < 1e-6:
		lateral_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
		lw = 1.0
	else:
		lateral_axis = lateral_axis / lw

	thumb_tip = pts3[4]
	lateral_offset = float(np.dot(thumb_tip - palm_center, lateral_axis))
	lateral_norm = lateral_offset / (lw + 1e-6)
	z_diff = float(thumb_tip[2] - palm_center[2])

	LATERAL_THRESH = 0.50
	DEPTH_GATE = -0.05
	thumb = (abs(lateral_norm) > LATERAL_THRESH) and (z_diff > DEPTH_GATE)

	index = bool(pts2[8, 1] < pts2[6, 1])
	middle = bool(pts2[12, 1] < pts2[10, 1])
	ring = bool(pts2[16, 1] < pts2[14, 1])
	pinky = bool(pts2[20, 1] < pts2[18, 1])

	return {"thumb": thumb, "index": index, "middle": middle, "ring": ring, "pinky": pinky}


def main() -> None:
	cap = cv2.VideoCapture(0)
	if not cap.isOpened():
		raise RuntimeError("Unable to open camera (index 0)")

	# MediaPipe Hands configuration
	with mp_hands.Hands(
		static_image_mode=False,
		max_num_hands=2,
		model_complexity=1,
		min_detection_confidence=0.5,
		min_tracking_confidence=0.5,
	) as hands:
		window = "Hand Tracking (MediaPipe)"
		cv2.namedWindow(window, cv2.WINDOW_NORMAL)

		# Persistent indicator (always drawn); value reflects current-frame gesture status
		spell_on = False

		while True:
			ok, frame = cap.read()
			if not ok:
				break

			# Mirror for a natural selfie-view
			frame = cv2.flip(frame, 1)

			# Convert BGR -> RGB for MediaPipe
			rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			rgb.flags.writeable = False
			results = hands.process(rgb)
			results = cast(Any, results)  # relax typing for convenient attribute access
			rgb.flags.writeable = True

			h, w = frame.shape[:2]

			both_ok = False
			ok_count = 0
			if getattr(results, "multi_hand_landmarks", None) and getattr(results, "multi_handedness", None):
				for hand_landmarks, hand_handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
					label = hand_handedness.classification[0].label  # "Left" or "Right"

					# Draw landmarks
					mp_drawing.draw_landmarks(
						frame,
						hand_landmarks,
						list(mp_hands.HAND_CONNECTIONS),
						mp_styles.get_default_hand_landmarks_style(),
						mp_styles.get_default_hand_connections_style(),
					)

					# Finger counting and states
					cnt = count_fingers(hand_landmarks.landmark, label)
					states = finger_states(hand_landmarks.landmark)

					# Check gesture: thumb, index, middle extended; ring, pinky contracted
					gesture_ok = (
						states["thumb"] and states["index"] and states["middle"] and (not states["ring"]) and (not states["pinky"])
					)
					ok_count += int(gesture_ok)

					# Annotate with label and count near the wrist (landmark 0)
					wrist = hand_landmarks.landmark[0]
					x_px, y_px = int(wrist.x * w), int(wrist.y * h)
					text = f"{label}: {cnt} fingers"
					cv2.putText(
						frame,
						text,
						(x_px + 10, y_px - 10),
						cv2.FONT_HERSHEY_SIMPLEX,
						0.8,
						(0, 255, 0),
						2,
						cv2.LINE_AA,
					)

			# Bool is true whenever both hands satisfy the gesture in this frame
            # and false otherwise.
			spell_on = (ok_count >= 2)

			# Persistent indicator in the top-left corner
			indicator = f"Spell: {'ON' if spell_on else 'OFF'}"
			cv2.rectangle(frame, (8, 8), (220, 46), (50, 50, 50), -1)
			cv2.putText(
				frame,
				indicator,
				(16, 36),
				cv2.FONT_HERSHEY_SIMPLEX,
				0.9,
				(0, 255, 0) if spell_on else (0, 0, 255),
				2,
				cv2.LINE_AA,
			)

			cv2.imshow(window, frame)
			key = cv2.waitKey(1) & 0xFF
			if key == ord('q'):
				break

	cap.release()
	cv2.destroyAllWindows()


if __name__ == "__main__":
	main()
