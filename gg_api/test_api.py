# gg_api/test_api.py

import json
import os
import requests  # Sử dụng thư viện requests

def test_api_key(api_key: str) -> dict:
    """
    Kiểm tra API key bằng cách gửi yêu cầu trực tiếp đến Google AI endpoint
    với timeout là 10 giây.
    """
    if not api_key:
        return {"success": False, "message": "No API key provided"}

    # Thông tin endpoint cho Gemini 1.5 Flash (một mô hình nhanh và nhẹ để test)
    model_name = "gemini-2.5-pro"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    # Dữ liệu gửi đi (một prompt đơn giản)
    payload = {
        "contents": [{
            "parts": [{"text": "Say 'ok'"}]
        }]
    }

    try:
        # Gửi yêu cầu POST với timeout là 10 giây
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(payload), 
            timeout=10  # <<< ĐÂY LÀ PHẦN QUAN TRỌNG NHẤT >>>
        )

        # Kiểm tra mã trạng thái HTTP
        if response.status_code == 200:
            return {
                "success": True, 
                "message": "✅ API key hợp lệ!",
                "text_model": model_name
            }
        else:
            # Cố gắng đọc lỗi từ phản hồi của Google
            error_details = response.json()
            error_message = error_details.get("error", {}).get("message", "Lỗi không xác định.")
            return {
                "success": False, 
                "message": f"❌ {error_message}"
            }

    except requests.exceptions.Timeout:
        # Bắt lỗi timeout sau 10 giây
        return {
            "success": False, 
            "message": "❌ Lỗi: Timeout sau 10 giây. Máy chủ không phản hồi."
        }
    except requests.exceptions.RequestException as e:
        # Bắt các lỗi mạng khác
        return {
            "success": False, 
            "message": f"❌ Lỗi mạng: {str(e)}"
        }
    except Exception as e:
        # Bắt các lỗi khác
        return {
            "success": False, 
            "message": f"❌ Lỗi không xác định: {str(e)}"
        }