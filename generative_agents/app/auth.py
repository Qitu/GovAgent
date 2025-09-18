from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from .config import Config

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 硬编码认证
        if username == Config.DEFAULT_USERNAME and password == Config.DEFAULT_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            flash('登录成功！', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('用户名或密码错误！', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已成功退出登录！', 'info')
    return redirect(url_for('auth.login'))