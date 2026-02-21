"""
AI Product Recognition Service
Nhận diện sản phẩm qua hình ảnh camera bằng Computer Vision.

Architecture:
- Mobile app gửi ảnh frame từ camera lên API
- Backend dùng OpenCV để preprocess ảnh
- TensorFlow Lite model inference để classify sản phẩm
- Trả về product_id + confidence score
- Fallback sang barcode scan nếu confidence thấp
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Threshold để accept kết quả nhận diện
CONFIDENCE_THRESHOLD = 0.75
# Số sản phẩm top-k trả về khi uncertain
TOP_K_RESULTS = 3


class ProductRecognitionResult:
    """Kết quả nhận diện sản phẩm."""

    def __init__(
        self,
        product_id: Optional[str],
        confidence: float,
        top_k: list[dict],
        method: str,
    ):
        self.product_id = product_id
        self.confidence = confidence
        self.top_k = top_k  # [{product_id, confidence, name}]
        self.method = method  # 'ai' | 'barcode' | 'fallback'
        self.success = product_id is not None and confidence >= CONFIDENCE_THRESHOLD


class ProductRecognitionService:
    """
    Service nhận diện sản phẩm qua hình ảnh.

    Trong production: dùng TensorFlow Lite model đã train.
    Hiện tại: skeleton code sẵn sàng tích hợp model thực.
    """

    def __init__(self):
        self._model = None
        self._label_map: dict[int, str] = {}  # index -> product_id
        self._is_loaded = False

    def load_model(self, model_path: str, label_map_path: str) -> None:
        """
        Load TFLite model và label map.

        Args:
            model_path: Đường dẫn file .tflite
            label_map_path: Đường dẫn file label map JSON
        """
        try:
            import tensorflow as tf  # type: ignore
            import json

            interpreter = tf.lite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            self._model = interpreter

            with open(label_map_path) as f:
                self._label_map = json.load(f)

            self._is_loaded = True
            logger.info(f"AI model loaded: {model_path}, labels: {len(self._label_map)}")

        except ImportError:
            logger.warning("TensorFlow not installed. AI recognition disabled.")
        except Exception as e:
            logger.error(f"Failed to load AI model: {e}")

    def _preprocess_image(self, image_bytes: bytes) -> "np.ndarray":  # type: ignore
        """
        Preprocess ảnh trước khi inference.
        - Resize về 224x224 (MobileNetV3 input)
        - Normalize pixel values [0, 1]
        - Convert BGR -> RGB
        """
        import numpy as np
        import cv2  # type: ignore

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)
        return img

    def _run_inference(self, preprocessed: "np.ndarray") -> list[tuple[int, float]]:  # type: ignore
        """
        Chạy TFLite inference, trả về list (class_index, confidence).
        Sorted by confidence descending.
        """
        import numpy as np

        input_details = self._model.get_input_details()
        output_details = self._model.get_output_details()

        self._model.set_tensor(input_details[0]["index"], preprocessed)
        self._model.invoke()

        output = self._model.get_tensor(output_details[0]["index"])[0]
        top_k_indices = np.argsort(output)[::-1][:TOP_K_RESULTS]

        return [(int(i), float(output[i])) for i in top_k_indices]

    async def recognize_from_base64(
        self, image_b64: str, store_product_ids: list[str]
    ) -> ProductRecognitionResult:
        """
        Nhận diện sản phẩm từ ảnh base64.

        Args:
            image_b64: Base64 encoded image (JPEG/PNG từ camera)
            store_product_ids: Danh sách product_id hợp lệ của store (để filter)

        Returns:
            ProductRecognitionResult
        """
        image_bytes = base64.b64decode(image_b64)
        return await self.recognize_from_bytes(image_bytes, store_product_ids)

    async def recognize_from_bytes(
        self, image_bytes: bytes, store_product_ids: list[str]
    ) -> ProductRecognitionResult:
        """
        Nhận diện sản phẩm từ raw image bytes.
        """
        if not self._is_loaded or self._model is None:
            # Model chưa load - trả về fallback
            logger.warning("AI model not loaded, returning fallback result")
            return ProductRecognitionResult(
                product_id=None,
                confidence=0.0,
                top_k=[],
                method="fallback",
            )

        try:
            preprocessed = self._preprocess_image(image_bytes)
            predictions = self._run_inference(preprocessed)

            top_k_results = []
            for class_idx, confidence in predictions:
                product_id = self._label_map.get(class_idx)
                if product_id and product_id in store_product_ids:
                    top_k_results.append({
                        "product_id": product_id,
                        "confidence": round(confidence, 4),
                    })

            if not top_k_results:
                return ProductRecognitionResult(
                    product_id=None,
                    confidence=0.0,
                    top_k=[],
                    method="ai",
                )

            best = top_k_results[0]
            return ProductRecognitionResult(
                product_id=best["product_id"] if best["confidence"] >= CONFIDENCE_THRESHOLD else None,
                confidence=best["confidence"],
                top_k=top_k_results,
                method="ai",
            )

        except Exception as e:
            logger.error(f"AI recognition error: {e}")
            return ProductRecognitionResult(
                product_id=None,
                confidence=0.0,
                top_k=[],
                method="fallback",
            )


# Singleton instance
recognition_service = ProductRecognitionService()
