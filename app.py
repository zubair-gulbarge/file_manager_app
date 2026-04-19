import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, File
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

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
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- AUTHENTICATION ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
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

# --- ADMIN MANAGEMENT ---

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
            flash(f"User {username} created!")
    return render_template('create_user.html')

# --- FILE CRUD OPERATIONS ---

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        files = File.query.all()
    else:
        files = File.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash("No file part", "danger")
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash("No selected file", "warning")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_file = File(filename=filename, user_id=current_user.id)
        db.session.add(new_file)
        db.session.commit()
        flash(f"Successfully uploaded {filename}", "success")
    else:
        flash("File type not allowed!", "danger")
    return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    file_record = File.query.filter_by(filename=filename).first_or_404()
    
    # Permission check: Only owner or admin can download
    if current_user.role != 'admin' and file_record.user_id != current_user.id:
        flash("Unauthorized download attempt!", "danger")
        return redirect(url_for('dashboard'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/rename/<int:file_id>', methods=['POST'])
@login_required
def rename_file(file_id):
    file_record = File.query.get_or_404(file_id)
    if current_user.role != 'admin' and file_record.user_id != current_user.id:
        return "Unauthorized", 403

    new_name = request.form.get('new_name')
    if new_name:
        old_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.filename)
        ext = file_record.filename.rsplit('.', 1)[1]
        safe_new_name = secure_filename(f"{new_name}.{ext}")
        new_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_new_name)
        
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            file_record.filename = safe_new_name
            db.session.commit()
            flash("File renamed successfully!")
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:file_id>')
@login_required
def delete_file(file_id):
    file_to_delete = File.query.get_or_404(file_id)
    if current_user.role != 'admin' and file_to_delete.user_id != current_user.id:
        flash("Unauthorized!")
        return redirect(url_for('dashboard'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_to_delete.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(file_to_delete)
    db.session.commit()
    flash("File deleted successfully.")
    return redirect(url_for('dashboard'))

# --- START SERVER ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)