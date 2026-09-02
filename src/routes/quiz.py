from flask import Blueprint, jsonify, request
import os
import requests
import json
from datetime import datetime

quiz_bp = Blueprint('quiz', __name__)

# BigMailer API 配置
BIGMAILER_API_KEY = os.environ.get("BIGMAILER_API_KEY", "")
BIGMAILER_BRAND_ID = os.environ.get("BIGMAILER_BRAND_ID", "5d542e26-bc9f-4939-96b4-6e130bc0a971")
BIGMAILER_LIST_ID = os.environ.get("BIGMAILER_LIST_ID", "f2685361-d605-47e5-bdfe-f3d2b0a65cfe")
BIGMAILER_BASE_URL = "https://api.bigmailer.io/v1"

@quiz_bp.route('/submit-email', methods=['POST'])
def submit_email():
    """
    处理Quiz邮箱提交，将邮箱添加到BigMailer列表
    """
    try:
        # 获取请求数据
        data = request.json
        if not data or 'email' not in data:
            return jsonify({'error': 'Email is required'}), 400
        
        email = data['email'].strip().lower()
        quiz_answers = data.get('answers', {})
        
        # 验证邮箱格式
        if not email or '@' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
        
        # 准备BigMailer API请求
        bigmailer_url = f"{BIGMAILER_BASE_URL}/brands/{BIGMAILER_BRAND_ID}/contacts"
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'X-API-Key': BIGMAILER_API_KEY
        }
        
        # 准备请求体
        payload = {
            'email': email,
            'list_ids': [BIGMAILER_LIST_ID],
            'unsubscribe_all': False
        }
        
        # 暂时注释掉field_values，先测试基本功能
        # if quiz_answers:
        #     field_values = []
        #     for question_id, answer in quiz_answers.items():
        #         field_values.append({
        #             'name': f'quiz_q{question_id}',
        #             'value': str(answer)
        #         })
        #     
        #     # 添加提交时间
        #     field_values.append({
        #         'name': 'quiz_submitted_at',
        #         'value': datetime.now().isoformat()
        #     })
        #     
        #     payload['field_values'] = field_values
        
        # 调用BigMailer API
        params = {'validate': 'true'}  # 启用邮箱验证
        response = requests.post(
            bigmailer_url,
            headers=headers,
            params=params,
            json=payload,
            timeout=10
        )
        
        # 处理BigMailer API响应
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Email successfully added to mailing list',
                'email': email
            }), 200
        elif response.status_code == 422:
            # 邮箱已存在
            return jsonify({
                'success': True,
                'message': 'Email already exists in our system',
                'email': email
            }), 200
        else:
            # 其他错误
            error_message = 'Failed to add email to mailing list'
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_message = error_data['message']
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': error_message,
                'status_code': response.status_code
            }), 400
    
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout. Please try again.'
        }), 408
    
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': 'Network error. Please try again later.'
        }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }), 500

@quiz_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查端点
    """
    return jsonify({
        'status': 'healthy',
        'service': 'quiz-backend',
        'timestamp': datetime.now().isoformat()
    }), 200

@quiz_bp.route('/test-bigmailer', methods=['POST'])
def test_bigmailer():
    """
    测试BigMailer API连接
    """
    try:
        # 测试API连接
        test_url = f"{BIGMAILER_BASE_URL}/brands/{BIGMAILER_BRAND_ID}/contacts"
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {BIGMAILER_API_KEY}'
        }
        
        # 发送GET请求测试连接
        response = requests.get(test_url, headers=headers, timeout=5)
        
        return jsonify({
            'bigmailer_connection': 'success' if response.status_code in [200, 401, 403] else 'failed',
            'status_code': response.status_code,
            'api_key_valid': response.status_code != 401,
            'brand_exists': response.status_code != 404
        }), 200
    
    except Exception as e:
        return jsonify({
            'bigmailer_connection': 'failed',
            'error': str(e)
        }), 500

