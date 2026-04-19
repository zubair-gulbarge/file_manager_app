import os
import math
from sqlalchemy import func
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, File
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Limit

# --- SECURITY (Rate Limiting) ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# --- DATABASE & LOGIN SETUP ---
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = "info"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'mov', 'docx'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- TEMPLATE FILTERS ---
@app.template_filter('format_size')
def format_size(size_bytes):
    if not size_bytes or size_bytes == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- AUTHENTICATION ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ADMIN & USER MANAGEMENT ---

@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash("Access Denied!")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')

        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
        else:
            new_user = User(
                username=username, 
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"User {username} created!", "success")
    return render_template('create_user.html')

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash("Access Denied!", "danger")
        return redirect(url_for('dashboard'))
        
    user = db.session.get(User, user_id)
    if user and user.id != current_user.id:
        user_files = File.query.filter_by(user_id=user.id).all()
        for f in user_files:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(f)
            
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.username} and their data removed.", "success")
    else:
        flash("Cannot delete yourself!", "warning")
    return redirect(url_for('dashboard'))

@app.route('/admin/toggle_role/<int:user_id>')
@login_required
def toggle_role(user_id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
    user = db.session.get(User, user_id)
    if user and user.id != current_user.id:
        user.role = 'admin' if user.role == 'user' else 'user'
        db.session.commit()
        flash(f"Role updated for {user.username}!", "success")
    return redirect(url_for('dashboard'))

# --- CORE DASHBOARD ---

@app.route('/dashboard')
@login_required
def dashboard():
    search_query = request.args.get('search', '').strip()
    
    if current_user.role == 'admin':
        files_query = File.query
    else:
        files_query = File.query.filter_by(user_id=current_user.id)
    
    if search_query:
        files = files_query.filter(File.filename.ilike(f"%{search_query}%")).all()
    else:
        files = files_query.all()

    analytics = None
    all_users = None
    
    if current_user.role == 'admin':
        all_users = User.query.all()
        user_stats = db.session.query(
            User.username, 
            func.sum(File.size).label('total_size'),
            func.count(File.id).label('file_count')
        ).join(File, isouter=True).group_by(User.username).all()

        category_stats = db.session.query(
            File.category, func.count(File.id).label('count')
        ).group_by(File.category).all()

        analytics = {
            'user_stats': user_stats,
            'category_stats': category_stats,
            'total_users': User.query.count()
        }

    total_usage = sum(f.size for f in files if f.size)
    usage_percent = min(round((total_usage / (16*1024*1024)) * 100, 1), 100)

    return render_template('dashboard.html', 
                           files=files, 
                           total_usage=total_usage, 
                           usage_percent=usage_percent,
                           analytics=analytics,
                           all_users=all_users)

# --- FILE OPERATIONS ---

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("No file part", "danger")
        return redirect(request.url)
    
    file = request.files['file']
    category = request.form.get('category', 'General')

    if file.filename == '':
        flash("No selected file", "warning")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        file_size = os.path.getsize(save_path)

        new_file = File(filename=filename, user_id=current_user.id, size=file_size, category=category)
        db.session.add(new_file)
        db.session.commit()
        flash(f"Successfully uploaded to {category}!", "success")
    else:
        flash("File type not allowed!", "danger")
    return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    file_record = File.query.filter_by(filename=filename).first_or_404()
    if current_user.role != 'admin' and file_record.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    mode = request.args.get('mode', 'view') 
    response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename))
    
    if mode == 'view':
        response.headers['Content-Disposition'] = 'inline'
    else:
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/delete/<int:file_id>')
@login_required
def delete_file(file_id):
    file_to_delete = File.query.get_or_404(file_id)
    if current_user.role != 'admin' and file_to_delete.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for('dashboard'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_to_delete.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(file_to_delete)
    db.session.commit()
    flash("File deleted successfully.")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)