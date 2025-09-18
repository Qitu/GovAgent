#!/usr/bin/env python3
"""
CRM管理系统主入口文件
"""

from app import create_app

# 创建Flask应用实例
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=True,
        use_reloader=False,
        threaded=True,
        host='0.0.0.0',
        port=5001
    )