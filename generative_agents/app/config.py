import os

class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    JSON_AS_ASCII = False
    
    # 模拟相关配置
    CHECKPOINTS_PATH = "results/checkpoints"
    COMPRESSED_PATH = "results/compressed"
    STATIC_ROOT = "frontend/static"
    
    # 认证配置
    DEFAULT_USERNAME = "admin"
    DEFAULT_PASSWORD = "admin123"