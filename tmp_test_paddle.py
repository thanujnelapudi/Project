import sys
import os
sys.path.append(r'c:\Users\Thanuj\OneDrive\ドキュメント\postal_ocr')
from paddleocr import PaddleOCR

try:
    paddle_ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    # create a dummy image
    from PIL import Image
    img = Image.new('RGB', (100, 30), color = (73, 109, 137))
    img.save('dummy.jpg')
    
    results = paddle_ocr.predict('dummy.jpg')
    print("Type of results:", type(results))
    for res in results:
        print("Attributes of res:", dir(res))
        for attr in dir(res):
            if not attr.startswith('__'):
                print(f"{attr}: {getattr(res, attr)}")
except Exception as e:
    print(f"Error: {e}")
