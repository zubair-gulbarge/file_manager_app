import unittest
from app import app, db, User, File
from werkzeug.security import generate_password_hash

class FileManagerTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        # SENIOR FIX: Use a helper to add users only if they don't exist
        self.create_test_data()

    def create_test_data(self):
        # Check if users already exist to prevent IntegrityError
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', 
                         password_hash=generate_password_hash('admin123'), 
                         role='admin')
            db.session.add(admin)
            
        if not User.query.filter_by(username='user1').first():
            user = User(username='user1', 
                        password_hash=generate_password_hash('user123'), 
                        role='user')
            db.session.add(user)
            
        db.session.commit()

    def tearDown(self):
        db.session.rollback() # Clear any pending transactions
        db.session.remove()   # Remove the session
        db.drop_all()         # Drop all tables
        self.app_context.pop()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    # --- TESTS ---

    def test_login_logout(self):
        response = self.login('admin', 'admin123')
        self.assertIn(b'Dashboard', response.data)
        
    def test_admin_access_user_management(self):
        self.login('admin', 'admin123')
        response = self.app.get('/admin/create_user')
        self.assertEqual(response.status_code, 200)
        
    def test_data_isolation(self):
        # Create a file owned by admin (ID 1)
        admin_file = File(filename='secret_admin.pdf', user_id=1)
        db.session.add(admin_file)
        db.session.commit()
        
        # Log in as regular user and try to delete it
        self.login('user1', 'user123')
        response = self.app.get(f'/delete/{admin_file.id}', follow_redirects=True)
        self.assertIn(b'Unauthorized!', response.data)

if __name__ == '__main__':
    unittest.main()