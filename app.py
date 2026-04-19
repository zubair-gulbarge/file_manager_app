import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from models import db, User, File
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123' # In production, use an env variable
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit 16MB

db.init_app(app)
login_manager = LoginManager(app)

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    # Senior Practice: Sanitize filename to prevent hacking
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Save to Database (CREATE)
    new_file = File(filename=filename, user_id=current_user.id)
    db.session.add(new_file)
    db.session.commit()
    
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # READ logic
    if current_user.role == 'admin':
        files = File.query.all()  # Admin sees everything
    else:
        files = File.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', files=files)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Generates the database file
    app.run(debug=True)