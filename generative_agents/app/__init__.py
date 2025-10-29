from flask import Flask
from .config import Config
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

def create_app():
    """应用工厂函数"""
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
        static_url_path="/static",
    )
    
    # 加载配置
    app.config.from_object(Config)
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 注册错误处理
    from .errors import register_error_handlers
    register_error_handlers(app)

    @app.route('/metrics')
    def metrics():
        return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    
    return app