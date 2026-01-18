from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_manager = db.Column(db.Boolean, default=False)  # Can edit current campaign
    is_admin = db.Column(db.Boolean, default=False)    # Full access (create/close campaigns, manage users)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def role(self):
        """Return user's role as string"""
        if self.is_admin:
            return 'admin'
        elif self.is_manager:
            return 'manager'
        else:
            return 'public'


class AssetLibrary(db.Model):
    """Library of assets that can be imported into campaigns"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., "Modern Warfare", "WWII", "Sci-Fi"
    is_default = db.Column(db.Boolean, default=False)  # Default libraries loaded for new campaigns
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assets = db.relationship('Asset', backref='library', lazy=True, cascade='all, delete-orphan')


class Asset(db.Model):
    """Individual asset within a library"""
    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('asset_library.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Vehicle, Weapon, Equipment, etc.
    category = db.Column(db.String(50))  # Subcategory like "Ground Vehicle", "Assault Rifle"
    description = db.Column(db.Text)
    default_quantity = db.Column(db.Integer, default=1)  # Default quantity when imported
    is_unique = db.Column(db.Boolean, default=False)
    show_in_public = db.Column(db.Boolean, default=True)  # Show this asset in public view
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=False)
    is_closed = db.Column(db.Boolean, default=False)
    map_edit_url = db.Column(db.String(500))  # Editorial link for admins/managers
    map_view_url = db.Column(db.String(500))  # View link for public
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    imported_libraries = db.relationship('CampaignLibraryImport', backref='campaign', lazy=True, cascade='all, delete-orphan')
    asset_pool = db.relationship('CampaignAsset', backref='campaign', lazy=True, cascade='all, delete-orphan')
    missions = db.relationship('Mission', backref='campaign', lazy=True)


class CampaignLibraryImport(db.Model):
    """Track which libraries are imported into a campaign"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    library_id = db.Column(db.Integer, db.ForeignKey('asset_library.id'), nullable=False)
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    library = db.relationship('AssetLibrary', backref='campaign_imports')


class CampaignAsset(db.Model):
    """Assets available in a campaign's pool (from imported libraries)"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    library_id = db.Column(db.Integer, db.ForeignKey('asset_library.id'), nullable=False)
    initial_quantity = db.Column(db.Integer, default=1)
    current_quantity = db.Column(db.Integer, default=1)
    
    # Relationships
    asset = db.relationship('Asset', backref='campaign_assets')
    library = db.relationship('AssetLibrary')


class Mission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    mission_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='planned')
    order_index = db.Column(db.Integer, default=0)
    map_edit_url = db.Column(db.String(500))  # Editorial link for admins/managers
    map_view_url = db.Column(db.String(500))  # View link for public
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    events = db.relationship('Event', backref='mission', lazy=True, cascade='all, delete-orphan')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('mission.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # combat, logistics, training, other
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    asset_changes = db.relationship('AssetChange', backref='event', lazy=True, cascade='all, delete-orphan')


class AssetChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'))
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id', ondelete='CASCADE'))
    quantity_change = db.Column(db.Integer, nullable=False)  # Positive = gain, Negative = loss
    notes = db.Column(db.Text)
    
    # Relationship
    asset = db.relationship('Asset', backref='asset_changes')


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))