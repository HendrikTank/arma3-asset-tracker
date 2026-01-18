import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
import unittest
from flask import url_for
from app import create_app, db
from app.models import User, Campaign, Asset, Mission, Event, CampaignAsset

class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.create_test_data()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def create_test_data(self):
        admin = User(username='admin', email='admin@test.com', is_admin=True)
        admin.set_password('password')
        manager = User(username='manager', email='manager@test.com', is_manager=True)
        manager.set_password('password')
        
        db.session.add(admin)
        db.session.add(manager)
        db.session.commit()
        
        asset = Asset(name='Tank', type='Vehicle')
        db.session.add(asset)
        db.session.commit()
    
    def login(self, username, password):
        return self.client.post(url_for('auth.login'), data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def test_index_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_timeline_page(self):
        response = self.client.get('/timeline')
        self.assertEqual(response.status_code, 200)
    
    def test_admin_dashboard_requires_login(self):
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 302)
    
    def test_admin_dashboard_requires_admin(self):
        self.login('manager', 'password')
        response = self.client.get('/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 403)
    
    def test_current_pool_api(self):
        response = self.client.get('/api/current-pool')
        self.assertEqual(response.status_code, 200)
    
    def test_manage_assets_requires_manager(self):
        response = self.client.get('/admin/assets')
        self.assertEqual(response.status_code, 302)

    def test_login_admin_user(self):
        response = self.login('admin', 'password')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'admin', response.data)

    def test_login_invalid_credentials(self):
        response = self.login('admin', 'wrongpassword')
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_accessible_for_admin(self):
        self.login('admin', 'password')
        response = self.client.get('/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_manage_assets_accessible_for_manager(self):
        self.login('manager', 'password')
        response = self.client.get('/admin/assets', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_manage_assets_requires_login(self):
        response = self.client.get('/admin/assets')
        self.assertEqual(response.status_code, 302)

    def test_user_has_correct_role(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            manager = User.query.filter_by(username='manager').first()
            self.assertEqual(admin.role, 'admin')
            self.assertEqual(manager.role, 'manager')

    def test_campaign_creation(self):
        with self.app.app_context():
            campaign = Campaign(name='Test Campaign', description='A test campaign')
            db.session.add(campaign)
            db.session.commit()
            self.assertIsNotNone(campaign.id)

    def test_mission_creation(self):
        with self.app.app_context():
            campaign = Campaign(name='Test Campaign')
            db.session.add(campaign)
            db.session.commit()
            mission = Mission(campaign_id=campaign.id, name='Test Mission', mission_date='2024-01-01')
            db.session.add(mission)
            db.session.commit()
            self.assertEqual(mission.campaign_id, campaign.id)

    def test_asset_change_tracking(self):
        with self.app.app_context():
            campaign = Campaign(name='Test Campaign')
            asset = Asset(name='Soldier', type='Personnel')
            mission = Mission(campaign_id=campaign.id, name='Test Mission', mission_date='2024-01-01')
            db.session.add_all([campaign, asset, mission])
            db.session.commit()
            event = Event(mission_id=mission.id, event_type='combat', title='Skirmish', event_date='2024-01-01')
            db.session.add(event)
            db.session.commit()
            asset_change = AssetChange(event_id=event.id, asset_id=asset.id, quantity_change=-5)
            db.session.add(asset_change)
            db.session.commit()
            self.assertEqual(asset_change.quantity_change, -5)
    def test_event_creation(self):
        with self.app.app_context():
            campaign = Campaign(name='Test Campaign')
            mission = Mission(campaign_id=campaign.id, name='Test Mission', mission_date='2024-01-01')
            db.session.add_all([campaign, mission])
            db.session.commit()
            event = Event(mission_id=mission.id, event_type='combat', title='Battle', event_date='2024-01-01')
            db.session.add(event)
            db.session.commit()
            self.assertEqual(event.mission_id, mission.id)
            self.assertEqual(event.event_type, 'combat')

    def test_campaign_asset_relationship(self):
        with self.app.app_context():
            campaign = Campaign(name='Test Campaign')
            asset = Asset(name='Helicopter', type='Vehicle')
            db.session.add_all([campaign, asset])
            db.session.commit()
            campaign_asset = CampaignAsset(campaign_id=campaign.id, asset_id=asset.id, quantity=10)
            db.session.add(campaign_asset)
            db.session.commit()
            self.assertEqual(campaign_asset.quantity, 10)

    def test_logout_user(self):
        self.login('admin', 'password')
        response = self.client.get(url_for('auth.logout'), follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_access_admin_dashboard(self):
        self.login('manager', 'password')
        response = self.client.get('/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 403)

    def test_asset_details(self):
        with self.app.app_context():
            asset = Asset.query.filter_by(name='Tank').first()
            self.assertIsNotNone(asset)
            self.assertEqual(asset.type, 'Vehicle')

    def test_user_password_hashing(self):
        with self.app.app_context():
            user = User.query.filter_by(username='admin').first()
            self.assertFalse(user.check_password('wrongpassword'))
            self.assertTrue(user.check_password('password'))


if __name__ == '__main__':
    unittest.main()