from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file, make_response, session
from flask_login import login_required, current_user
from app import db
from app.models import Campaign, Asset, CampaignAsset, Mission, Event, AssetChange, Log, User, AssetLibrary, CampaignLibraryImport
from datetime import datetime
import json
import csv
import io
import os

main = Blueprint('main', __name__)

# Public routes
@main.route('/')
def index():
    current_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    missions_list = []
    
    if current_campaign:
        # Get assets - using new CampaignAsset model, filter by show_in_public
        campaign_assets = CampaignAsset.query.filter_by(campaign_id=current_campaign.id).all()
        asset_list = [{
            'name': ca.asset.name,
            'type': ca.asset.type,
            'category': ca.asset.category,
            'current_quantity': ca.current_quantity,
            'library_name': ca.library.name
        } for ca in campaign_assets if ca.asset.show_in_public]  # Filter here
        
        # Get missions with events grouped
        missions = Mission.query.filter_by(campaign_id=current_campaign.id).order_by(Mission.mission_date.desc()).all()
        for mission in missions:
            mission_events = []
            for event in mission.events:
                event_data = {
                    'title': event.title,
                    'date': event.event_date,
                    'type': event.event_type,
                    'description': event.description,
                    'location': event.location
                }
                mission_events.append(event_data)
            
            missions_list.append({
                'id': mission.id,
                'name': mission.name,
                'date': mission.mission_date,
                'description': mission.description,
                'location': mission.location,
                'status': mission.status,
                'events': mission_events,
                'event_count': len(mission_events),
                'map_view_url': mission.map_view_url,
                'map_edit_url': mission.map_edit_url
            })
    else:
        asset_list = []
    
    return render_template('public/dashboard.html', 
                         campaign=current_campaign, 
                         assets=asset_list,
                         missions=missions_list)

@main.route('/api/current-pool')
def current_pool():
    current_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    if not current_campaign:
        return jsonify([])
    
    assets = CampaignAsset.query.filter_by(campaign_id=current_campaign.id).all()
    return jsonify([{
        'name': lib.asset.name,
        'type': lib.asset.type,
        'current_quantity': lib.current_quantity
    } for lib in assets])

@main.route('/timeline')
def timeline():
    current_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    events_list = []
    
    if current_campaign:
        missions = Mission.query.filter_by(campaign_id=current_campaign.id).order_by(Mission.order_index).all()
        for mission in missions:
            for event in mission.events:
                # Get asset changes for this event
                asset_changes = []
                for change in event.asset_changes:
                    asset_changes.append({
                        'asset_name': change.asset.name,
                        'asset_type': change.asset.type,
                        'quantity_change': change.quantity_change
                    })
                
                events_list.append({
                    'title': f"{mission.name}: {event.title}",
                    'date': event.event_date.strftime('%Y-%m-%d %H:%M'),
                    'type': event.event_type,
                    'description': event.description or event.notes or '',
                    'asset_changes': asset_changes
                })
    
    # Sort events by date (newest first)
    events_list.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('public/timeline.html', events=events_list)

# Admin routes - require login
@main.route('/admin')
@login_required
def admin_dashboard():
    """Admin Dashboard - Full access"""
    if not current_user.is_admin:
        # Redirect managers to their dashboard
        if current_user.is_manager:
            return redirect(url_for('main.manager_dashboard'))
        
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    active_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    
    return render_template('admin/dashboard.html', 
                         campaigns=campaigns,
                         active_campaign=active_campaign)

# Mission Management Routes
@main.route('/admin/campaign/<int:campaign_id>/missions')
@login_required
def campaign_missions(campaign_id):
    """View and manage missions for a campaign"""
    if not (current_user.is_manager or current_user.is_admin):
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Managers can only access active campaign
    if current_user.is_manager and not current_user.is_admin:
        if not campaign.is_active:
            flash('Managers can only access the active campaign.', 'error')
            return redirect(url_for('main.manager_dashboard'))
    
    missions = Mission.query.filter_by(campaign_id=campaign_id).all()
    
    # Get max order index for new mission
    max_order = db.session.query(db.func.max(Mission.order_index)).filter_by(
        campaign_id=campaign_id
    ).scalar() or 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/missions.html', 
                         campaign=campaign, 
                         missions=missions,
                         max_order=max_order,
                         today=today)

@main.route('/admin/mission/add', methods=['POST'])
@login_required
def add_mission():
    """Add a new mission"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        campaign_id = request.form['campaign_id']
        
        # Fix: Handle empty order_index gracefully
        order_index_str = request.form.get('order_index', '0')
        order_index = int(order_index_str) if order_index_str.strip() else 0
        
        mission = Mission(
            campaign_id=campaign_id,
            name=request.form['name'],
            description=request.form.get('description', ''),
            mission_date=datetime.strptime(request.form['mission_date'], '%Y-%m-%d'),
            location=request.form.get('location', ''),
            status=request.form.get('status', 'planned'),
            order_index=order_index,
            map_edit_url=request.form.get('map_edit_url', ''),
            map_view_url=request.form.get('map_view_url', '')
        )
        
        db.session.add(mission)
        db.session.commit()
        
        flash(f'Mission "{mission.name}" added successfully!', 'success')
        return redirect(url_for('main.campaign_missions', campaign_id=campaign_id))
    except Exception as e:
        flash(f'Error adding mission: {str(e)}', 'error')
        # Fix: Handle missing campaign_id
        campaign_id = request.form.get('campaign_id')
        if campaign_id:
            return redirect(url_for('main.campaign_missions', campaign_id=campaign_id))
        else:
            return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/mission/edit', methods=['POST'])
@login_required
def edit_mission():
    """Edit an existing mission"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        mission_id = request.form['mission_id']
        mission = Mission.query.get_or_404(mission_id)
        
        mission.name = request.form['name']
        mission.description = request.form.get('description', '')
        mission.mission_date = datetime.strptime(request.form['mission_date'], '%Y-%m-%d')
        mission.location = request.form.get('location', '')
        mission.status = request.form.get('status', 'planned')
        mission.map_edit_url = request.form.get('map_edit_url', '')
        mission.map_view_url = request.form.get('map_view_url', '')
        
        # Fix: Handle empty order_index gracefully
        order_index_str = request.form.get('order_index', '0')
        mission.order_index = int(order_index_str) if order_index_str.strip() else 0
        
        db.session.commit()
        
        flash(f'Mission "{mission.name}" updated successfully!', 'success')
        # Fix: Use the mission's campaign_id, not from form
        return redirect(url_for('main.campaign_missions', campaign_id=mission.campaign_id))
        
    except Exception as e:
        flash(f'Error updating mission: {str(e)}', 'error')
        # Fix: Use the mission's campaign_id if available, otherwise redirect to admin dashboard
        if 'mission' in locals():
            return redirect(url_for('main.campaign_missions', campaign_id=mission.campaign_id))
        else:
            return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/mission/delete', methods=['POST'])
@login_required
def delete_mission():
    """Delete a mission"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        mission_id = request.form['mission_id']
        mission = Mission.query.get_or_404(mission_id)
        campaign_id = mission.campaign_id
        
        # Delete associated events and asset changes
        db.session.delete(mission)
        db.session.commit()
        
        flash(f'Mission "{mission.name}" deleted successfully!', 'success')
        return redirect(url_for('main.campaign_missions', campaign_id=campaign_id))
    except Exception as e:
        flash(f'Error deleting mission: {str(e)}', 'error')
        return redirect(url_for('main.campaign_missions', campaign_id=campaign_id))

# Event Management Routes
@main.route('/admin/mission/<int:mission_id>/events')
@login_required
def mission_events(mission_id):
    """View and manage events for a mission"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    mission = Mission.query.get_or_404(mission_id)
    events = Event.query.filter_by(mission_id=mission_id).order_by(Event.event_date).all()
    
    # Get campaign assets for adding asset changes
    campaign_assets = CampaignAsset.query.filter_by(
        campaign_id=mission.campaign_id
    ).all()
    
    # Calculate statistics
    total_asset_changes = 0
    asset_gains = 0
    asset_losses = 0
    
    for event in events:
        for change in event.asset_changes:
            total_asset_changes += 1
            if change.quantity_change > 0:
                asset_gains += change.quantity_change
            else:
                asset_losses += abs(change.quantity_change)
    
    # Default event time (mission date at 12:00)
    # Convert mission_date (date) to datetime for the form
    from datetime import datetime, time
    default_event_datetime = datetime.combine(mission.mission_date, time(12, 0))
    default_event_time = default_event_datetime.strftime('%Y-%m-%dT%H:%M')
    
    return render_template('admin/events.html',
                         mission=mission,
                         events=events,
                         campaign_assets=campaign_assets,
                         total_asset_changes=total_asset_changes,
                         asset_gains=asset_gains,
                         asset_losses=asset_losses,
                         default_event_time=default_event_time)

@main.route('/admin/event/add', methods=['POST'])
@login_required
def add_event():
    """Add a new event"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        mission_id = request.form['mission_id']
        campaign_id = request.form['campaign_id']
        
        event = Event(
            mission_id=mission_id,
            title=request.form['title'],
            event_type=request.form['event_type'],
            description=request.form.get('description', ''),
            event_date=datetime.strptime(request.form['event_date'], '%Y-%m-%dT%H:%M'),
            location=request.form.get('location', ''),
            notes=request.form.get('notes', '')
        )
        
        db.session.add(event)
        db.session.flush()  # Get event ID
        
        # Process asset changes
        asset_changes_added = []
        i = 0
        while True:
            asset_key = f'asset_changes[{i}][asset_id]'
            if asset_key not in request.form:
                break
            
            asset_id = request.form.get(asset_key)
            if asset_id:  # Only process if asset is selected
                quantity_change = int(request.form.get(f'asset_changes[{i}][quantity_change]', 0))
                notes = request.form.get(f'asset_changes[{i}][notes]', '')
                
                if quantity_change != 0:  # Only add if there's an actual change
                    asset_change = AssetChange(
                        event_id=event.id,
                        asset_id=int(asset_id),
                        quantity_change=quantity_change,
                        notes=notes
                    )
                    db.session.add(asset_change)
                    
                    # Update campaign asset quantity
                    campaign_asset = CampaignAsset.query.filter_by(
                        campaign_id=campaign_id,
                        asset_id=asset_id
                    ).first()
                    
                    if campaign_asset:
                        campaign_asset.current_quantity += quantity_change
                        if campaign_asset.current_quantity < 0:
                            campaign_asset.current_quantity = 0

                    asset_changes_added.append({
                        'asset_id': asset_id,
                        'quantity_change': quantity_change
                    })
            
            i += 1
        
        db.session.commit()
        
        flash(f'Event "{event.title}" added successfully with {len(asset_changes_added)} asset changes!', 'success')
        return redirect(url_for('main.mission_events', mission_id=mission_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding event: {str(e)}', 'error')
        return redirect(url_for('main.mission_events', mission_id=request.form.get('mission_id')))

@main.route('/admin/event/edit', methods=['POST'])
@login_required
def edit_event():
    """Edit an existing event"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        event_id = request.form['event_id']
        event = Event.query.get_or_404(event_id)
        
        event.title = request.form['title']
        event.event_type = request.form['event_type']
        event.description = request.form.get('description', '')
        event.event_date = datetime.strptime(request.form['event_date'], '%Y-%m-%dT%H:%M')
        event.location = request.form.get('location', '')
        event.notes = request.form.get('notes', '')
        
        db.session.commit()
        
        flash(f'Event "{event.title}" updated successfully!', 'success')
        return redirect(url_for('main.mission_events', mission_id=event.mission_id))
    except Exception as e:
        flash(f'Error updating event: {str(e)}', 'error')
        return redirect(url_for('main.mission_events', mission_id=event.mission_id))

@main.route('/admin/event/delete', methods=['POST'])
@login_required
def delete_event():
    """Delete an event"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        event_id = request.form['event_id']
        event = Event.query.get_or_404(event_id)
        mission_id = event.mission_id
        
        # First, revert asset changes
        for change in event.asset_changes:
            # Find the campaign asset entry and revert the change
            campaign_asset = CampaignAsset.query.filter_by(
                campaign_id=event.mission.campaign_id,
                asset_id=change.asset_id
            ).first()
            
            if campaign_asset:
                campaign_asset.current_quantity -= change.quantity_change
                if campaign_asset.current_quantity < 0:
                    campaign_asset.current_quantity = 0
        
        # Delete the event (asset changes will cascade delete)
        db.session.delete(event)
        db.session.commit()
        
        flash(f'Event "{event.title}" deleted successfully!', 'success')
        return redirect(url_for('main.mission_events', mission_id=mission_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting event: {str(e)}', 'error')
        return redirect(url_for('main.mission_events', mission_id=mission_id))

# Asset Change Management Routes
@main.route('/admin/asset-change/add', methods=['POST'])
@login_required
def add_asset_change():
    """Add an asset change to an event"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'error': 'Unauthorized'}), 403
        else:
            return redirect(url_for('main.index'))
    
    try:
        event_id = request.form['event_id']
        event = Event.query.get_or_404(event_id)
        
        asset_change = AssetChange(
            event_id=event_id,
            asset_id=int(request.form['asset_id']),
            quantity_change=int(request.form['quantity_change']),
            notes=request.form.get('notes', '')
        )
        
        db.session.add(asset_change)
        
        # Update campaign asset quantity
        campaign_asset = CampaignAsset.query.filter_by(
            campaign_id=event.mission.campaign_id,
            asset_id=asset_change.asset_id
        ).first()
        
        if campaign_asset:
            campaign_asset.current_quantity += asset_change.quantity_change
            if campaign_asset.current_quantity < 0:
                campaign_asset.current_quantity = 0

        db.session.commit()
        
        flash('Asset change added successfully!', 'success')
        
        # Handle both AJAX and direct submissions
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'success': True})
        else:
            return redirect(url_for('main.mission_events', mission_id=event.mission_id))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding asset change: {str(e)}', 'error')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        else:
            # Try to redirect back to the event page if possible
            event_id = request.form.get('event_id')
            if event_id:
                try:
                    event = Event.query.get(event_id)
                    if event:
                        return redirect(url_for('main.mission_events', mission_id=event.mission_id))
                except:
                    pass
            return redirect(url_for('main.admin_dashboard'))

@main.route('/admin/asset-change/delete', methods=['POST'])
@login_required
def delete_asset_change():
    """Delete an asset change"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        change_id = request.form['change_id']
        change = AssetChange.query.get_or_404(change_id)
        event = change.event
        mission_id = event.mission_id
        
        # Revert the asset change in campaign asset
        campaign_asset = CampaignAsset.query.filter_by(
            campaign_id=event.mission.campaign_id,
            asset_id=change.asset_id
        ).first()
        
        if campaign_asset:
            campaign_asset.current_quantity -= change.quantity_change
            if campaign_asset.current_quantity < 0:
                campaign_asset.current_quantity = 0
        
        db.session.delete(change)
        db.session.commit()
        
        flash('Asset change removed successfully!', 'success')
        return redirect(url_for('main.mission_events', mission_id=mission_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error removing asset change: {str(e)}', 'error')
        return redirect(url_for('main.mission_events', mission_id=mission_id))

@main.route('/admin/campaign/<int:campaign_id>/report')
@login_required
def generate_campaign_report(campaign_id):
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    campaign = Campaign.query.get_or_404(campaign_id)
    report_data = generate_report_data(campaign)
    
    # Create CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Asset Name', 'Asset Type', 'Initial Quantity', 'Current Quantity', 'Net Change'])
    
    # Write data
    for item in report_data['asset_history']:
        writer.writerow([
            item['asset_name'],
            item['asset_type'],
            item['initial_quantity'],
            item['current_quantity'],
            item['net_change']
        ])
    
    output.seek(0)
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_report.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

def generate_report_data(campaign):
    """Generate report data for a campaign"""
    campaign_assets = CampaignAsset.query.filter_by(campaign_id=campaign.id).all()
    missions = Mission.query.filter_by(campaign_id=campaign.id).all()
    
    asset_history = []
    for ca in campaign_assets:
        asset_history.append({
            'asset_name': ca.asset.name,
            'asset_type': ca.asset.type,
            'initial_quantity': ca.initial_quantity,
            'current_quantity': ca.current_quantity,
            'net_change': ca.current_quantity - ca.initial_quantity
        })
    
    return {
        'campaign': {
            'name': campaign.name,
            'description': campaign.description,
            'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
            'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
            'is_closed': campaign.is_closed
        },
        'missions_count': len(missions),
        'asset_history': asset_history
    }

def generate_final_report(campaign):
    """Generate comprehensive final report for archiving"""
    report = generate_report_data(campaign)
    
    # Add detailed mission and event history
    missions = Mission.query.filter_by(campaign_id=campaign.id).all()
    detailed_missions = []
    
    for mission in missions:
        mission_data = {
            'name': mission.name,
            'date': mission.mission_date.isoformat() if mission.mission_date else None,
            'description': mission.description,
            'events': []
        }
        
        for event in mission.events:
            event_data = {
                'type': event.event_type,
                'description': event.description,
                'date': event.event_date.isoformat(),
                'notes': event.notes,
                'asset_changes': []
            }
            
            for change in event.asset_changes:
                event_data['asset_changes'].append({
                    'asset_name': change.asset.name,
                    'quantity_change': change.quantity_change,
                    'notes': change.notes
                })
            
            mission_data['events'].append(event_data)
        
        detailed_missions.append(mission_data)
    
    report['detailed_missions'] = detailed_missions
    
    # Add logs
    logs = Log.query.filter_by(campaign_id=campaign.id).all()
    report['logs'] = [{
        'action': log.action,
        'details': log.details,
        'created_at': log.created_at.isoformat() if log.created_at else None
    } for log in logs]
    
    return report

@main.route('/admin/assets', methods=['GET', 'POST'])
@login_required
def manage_assets():
    """Manage assets library"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            asset = Asset(
                name=request.form['name'],
                type=request.form['type'],
                category=request.form.get('category', ''),
                description=request.form.get('description', ''),
                is_unique=request.form.get('is_unique') == 'true'
            )
            db.session.add(asset)
            db.session.commit()
            flash(f'Asset "{asset.name}" added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding asset: {str(e)}', 'error')
        return redirect(url_for('main.manage_assets'))
    
    assets = Asset.query.order_by(Asset.name).all()
    return render_template('admin/assets.html', assets=assets)

@main.route('/admin/edit-asset', methods=['POST'])
@login_required
def edit_asset():
    """Edit an existing asset"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        asset_id = request.form['asset_id']
        asset = Asset.query.get_or_404(asset_id)
        
        asset.name = request.form['name']
        asset.type = request.form['type']
        asset.category = request.form.get('category', '')
        asset.description = request.form.get('description', '')
        asset.is_unique = request.form.get('is_unique') == 'true'
        
        db.session.commit()
        flash(f'Asset "{asset.name}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating asset: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_assets'))

@main.route('/admin/delete-asset', methods=['POST'])
@login_required
def delete_asset():
    """Delete an asset"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        asset_id = request.form['asset_id']
        asset = Asset.query.get_or_404(asset_id)
        
        # Check if asset is used in any campaigns
        campaigns_using = CampaignAsset.query.filter_by(asset_id=asset_id).count()
        if campaigns_using > 0:
            flash(f'Cannot delete "{asset.name}". It is used in {campaigns_using} campaign(s).', 'error')
        else:
            db.session.delete(asset)
            db.session.commit()
            flash(f'Asset "{asset.name}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting asset: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_assets'))

@main.route('/admin/campaigns', methods=['GET', 'POST'])
@login_required
def manage_campaigns():
    """Manage campaigns - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    if request.method == 'POST':
        try:
            # Check if user wants to set this as active
            set_as_active = request.form.get('set_active') == 'on'
            
            # If setting as active, deactivate all other campaigns first
            if set_as_active:
                Campaign.query.update({'is_active': False})
            
            campaign = Campaign(
                name=request.form['name'],
                description=request.form.get('description', ''),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d') if request.form.get('start_date') else None,
                map_edit_url=request.form.get('map_edit_url', ''),
                map_view_url=request.form.get('map_view_url', ''),
                is_active=set_as_active
            )
            
            db.session.add(campaign)
            db.session.flush()
            
            # Import selected libraries
            library_ids = request.form.getlist('import_libraries')
            if library_ids:
                for lib_id in library_ids:
                    library = AssetLibrary.query.get(lib_id)
                    if library:
                        # Create import record
                        library_import = CampaignLibraryImport(
                            campaign_id=campaign.id,
                            library_id=library.id
                        )
                        db.session.add(library_import)
                        
                        # Import all assets from library
                        for asset in library.assets:
                            campaign_asset = CampaignAsset(
                                campaign_id=campaign.id,
                                asset_id=asset.id,
                                library_id=library.id,
                                initial_quantity=asset.default_quantity,
                                current_quantity=asset.default_quantity
                            )
                            db.session.add(campaign_asset)
            
            db.session.commit()
            flash(f'Campaign "{campaign.name}" created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating campaign: {str(e)}', 'error')
        
        return redirect(url_for('main.manage_campaigns'))
    
    # GET request - show form
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    libraries = AssetLibrary.query.order_by(AssetLibrary.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/campaigns.html', 
                         campaigns=campaigns, 
                         libraries=libraries,
                         today=today)

@main.route('/admin/campaign/set-active', methods=['POST'])
@login_required
def set_campaign_active():
    """Set a campaign as active - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.manage_campaigns'))
    
    try:
        campaign_id = request.form['campaign_id']
        
        # Deactivate all campaigns
        Campaign.query.update({'is_active': False})
        
        # Activate selected campaign
        campaign = Campaign.query.get_or_404(campaign_id)
        campaign.is_active = True
        db.session.commit()
        
        flash(f'Campaign "{campaign.name}" is now active', 'success')
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'success': True, 'message': f'Campaign "{campaign.name}" is now active'})
        else:
            return redirect(url_for('main.manage_campaigns'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting campaign active: {str(e)}', 'error')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'error': str(e)}), 400
        else:
            return redirect(url_for('main.manage_campaigns'))

@main.route('/admin/campaign/close', methods=['POST'])
@login_required
def close_campaign():
    """Close a campaign"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.manage_campaigns'))
    
    try:
        campaign_id = request.form['campaign_id']
        campaign = Campaign.query.get_or_404(campaign_id)
        
        if campaign.is_closed:
            flash('Campaign already closed', 'warning')
            return redirect(url_for('main.manage_campaigns'))
        
        campaign.is_closed = True
        campaign.is_active = False
        campaign.end_date = datetime.utcnow().date()
        
        # Generate final report (simplified for now)
        import json
        import os
        
        report_data = {
            'campaign': {
                'name': campaign.name,
                'description': campaign.description,
                'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
                'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
                'status': 'closed'
            },
            'closed_at': datetime.utcnow().isoformat()
        }
        
        # Save report
        os.makedirs('/app/reports', exist_ok=True)
        report_filename = f"campaign_{campaign.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = f"/app/reports/{report_filename}"
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        db.session.commit()
        
        flash(f'Campaign "{campaign.name}" closed successfully. Report saved.', 'success')
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                'success': True,
                'message': f'Campaign "{campaign.name}" closed successfully',
                'report': report_filename
            })
        else:
            return redirect(url_for('main.manage_campaigns'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error closing campaign: {str(e)}', 'error')
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        else:
            return redirect(url_for('main.manage_campaigns'))

@main.route('/admin/campaign/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """View and manage a specific campaign"""
    if not (current_user.is_manager or current_user.is_admin):
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Managers can only access the active campaign
    if current_user.is_manager and not current_user.is_admin:
        if not campaign.is_active:
            flash('Managers can only access the active campaign.', 'error')
            return redirect(url_for('main.admin_dashboard'))
    
    # Get all available libraries
    all_libraries = AssetLibrary.query.order_by(AssetLibrary.name).all()
    
    # Get imported libraries
    imported_library_ids = [imp.library_id for imp in campaign.imported_libraries]
    imported_libraries = AssetLibrary.query.filter(AssetLibrary.id.in_(imported_library_ids)).all() if imported_library_ids else []
    
    # Get assets in campaign grouped by library
    campaign_assets = CampaignAsset.query.filter_by(campaign_id=campaign_id).all()
    assets_by_library = {}
    for ca in campaign_assets:
        lib_name = ca.library.name
        if lib_name not in assets_by_library:
            assets_by_library[lib_name] = []
        assets_by_library[lib_name].append(ca)
    
    return render_template('admin/campaign_detail.html',
                         campaign=campaign,
                         all_libraries=all_libraries,
                         imported_libraries=imported_libraries,
                         imported_library_ids=imported_library_ids,
                         campaign_assets=campaign_assets,
                         assets_by_library=assets_by_library)

@main.route('/admin/campaign/<int:campaign_id>/add-asset', methods=['POST'])
@login_required
def add_asset_to_campaign(campaign_id):
    """Add an asset to a campaign"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        asset_id = data['asset_id']
        quantity = data.get('quantity', 1)
        
        # Check if asset already in campaign
        existing = CampaignAsset.query.filter_by(
            campaign_id=campaign_id,
            asset_id=asset_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Asset already in campaign'}), 400
        
        # Get the asset to find its library
        asset = Asset.query.get_or_404(asset_id)
        
        # Add asset to campaign
        campaign_asset = CampaignAsset(
            campaign_id=campaign_id,
            asset_id=asset_id,
            library_id=asset.library_id,
            initial_quantity=quantity,
            current_quantity=quantity
        )
        
        db.session.add(campaign_asset)
        db.session.commit()
        
        return jsonify({'success': True, 'id': campaign_asset.id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@main.route('/api/update-asset-quantity', methods=['POST'])
@login_required
def update_asset_quantity():
    """Update initial quantity of an asset in a campaign"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        library_id = data['library_id']
        quantity = data['quantity']
        
        campaign_asset = CampaignAsset.query.get_or_404(library_id)
        
        # Update both initial and current quantities
        diff = quantity - campaign_asset.initial_quantity
        campaign_asset.initial_quantity = quantity
        campaign_asset.current_quantity += diff
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@main.route('/api/remove-asset-from-campaign', methods=['POST'])
@login_required
def remove_asset_from_campaign():
    """Remove an asset from a campaign"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        library_id = data['library_id']
        
        campaign_asset = CampaignAsset.query.get_or_404(library_id)
        db.session.delete(campaign_asset)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Asset Library Management Routes
@main.route('/admin/libraries')
@login_required
def manage_libraries():
    """Manage asset libraries"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    libraries = AssetLibrary.query.order_by(AssetLibrary.name).all()
    return render_template('admin/libraries.html', libraries=libraries)


@main.route('/admin/libraries/create', methods=['POST'])
@login_required
def create_library():
    """Create a new asset library"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        library = AssetLibrary(
            name=request.form['name'],
            description=request.form.get('description', ''),
            category=request.form.get('category', ''),
            is_default=request.form.get('is_default') == 'on'
        )
        db.session.add(library)
        db.session.commit()
        flash(f'Library "{library.name}" created successfully!', 'success')
    except Exception as e:
        flash(f'Error creating library: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_libraries'))


@main.route('/admin/libraries/<int:library_id>')
@login_required
def library_detail(library_id):
    """View and manage assets in a library"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    library = AssetLibrary.query.get_or_404(library_id)
    assets = Asset.query.filter_by(library_id=library_id).order_by(Asset.name).all()
    all_libraries = AssetLibrary.query.order_by(AssetLibrary.name).all()
    
    return render_template('admin/library_detail.html', 
                         library=library, 
                         assets=assets,
                         all_libraries=all_libraries)

@main.route('/admin/libraries/<int:library_id>/add-asset', methods=['POST'])
@login_required
def add_asset_to_library(library_id):
    """Add an asset to a library"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.manage_libraries'))
    
    try:
        asset = Asset(
            library_id=library_id,
            name=request.form['name'],
            type=request.form['type'],
            category=request.form.get('category', ''),
            description=request.form.get('description', ''),
            default_quantity=int(request.form.get('default_quantity', 1)),
            is_unique=request.form.get('is_unique') == 'on',
            show_in_public=request.form.get('show_in_public') == 'on'
        )
        db.session.add(asset)
        db.session.commit()
        flash(f'Asset "{asset.name}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding asset: {str(e)}', 'error')
    
    return redirect(url_for('main.library_detail', library_id=library_id))


@main.route('/admin/libraries/<int:library_id>/edit-asset/<int:asset_id>', methods=['POST'])
@login_required
def edit_library_asset(library_id, asset_id):
    """Edit an asset in a library"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.manage_libraries'))
    
    try:
        asset = Asset.query.get_or_404(asset_id)
        asset.name = request.form['name']
        asset.type = request.form['type']
        asset.category = request.form.get('category', '')
        asset.description = request.form.get('description', '')
        asset.default_quantity = int(request.form.get('default_quantity', 1))
        asset.is_unique = request.form.get('is_unique') == 'on'
        asset.show_in_public = request.form.get('show_in_public') == 'on'
        
        db.session.commit()
        flash(f'Asset "{asset.name}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating asset: {str(e)}', 'error')
    
    return redirect(url_for('main.library_detail', library_id=library_id))


@main.route('/admin/libraries/<int:library_id>/delete-asset', methods=['POST'])
@login_required
def delete_library_asset(library_id):
    """Delete an asset from a library"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        asset_id = request.form.get('asset_id')
        asset = Asset.query.filter_by(id=asset_id, library_id=library_id).first_or_404()
        
        # Check if asset is used in any campaigns
        campaigns_using = CampaignAsset.query.filter_by(asset_id=asset_id).count()
        if campaigns_using > 0:
            flash(f'Cannot delete "{asset.name}". It is used in {campaigns_using} campaign(s).', 'error')
        else:
            asset_name = asset.name
            db.session.delete(asset)
            db.session.commit()
            flash(f'Asset "{asset_name}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting asset: {str(e)}', 'error')
    
    return redirect(url_for('main.library_detail', library_id=library_id))


@main.route('/admin/libraries/<int:library_id>/delete', methods=['POST'])
@login_required
def delete_library(library_id):
    """Delete a library"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        library = AssetLibrary.query.get_or_404(library_id)
        
        # Check if library is used in any campaigns
        campaigns_using = CampaignLibraryImport.query.filter_by(library_id=library_id).count()
        if campaigns_using > 0:
            flash(f'Cannot delete library "{library.name}". It is used in {campaigns_using} campaign(s).', 'error')
        else:
            db.session.delete(library)
            db.session.commit()
            flash(f'Library "{library.name}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting library: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_libraries'))


@main.route('/admin/campaign/<int:campaign_id>/import-library', methods=['POST'])
@login_required
def import_library_to_campaign(campaign_id):
    """Import a library's assets into a campaign"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        library_id = int(request.form['library_id'])
        
        # Check if library already imported
        existing = CampaignLibraryImport.query.filter_by(
            campaign_id=campaign_id,
            library_id=library_id
        ).first()
        
        if existing:
            flash('Library already imported to this campaign.', 'warning')
            return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))
        
        # Create import record
        library_import = CampaignLibraryImport(
            campaign_id=campaign_id,
            library_id=library_id
        )
        db.session.add(library_import)
        
        # Import all assets from the library
        library = AssetLibrary.query.get_or_404(library_id)
        assets = Asset.query.filter_by(library_id=library_id).all()
        
        for asset in assets:
            # Check if asset already in campaign
            existing_asset = CampaignAsset.query.filter_by(
                campaign_id=campaign_id,
                asset_id=asset.id
            ).first()
            
            if not existing_asset:
                campaign_asset = CampaignAsset(
                    campaign_id=campaign_id,
                    asset_id=asset.id,
                    library_id=library_id,
                    initial_quantity=asset.default_quantity,
                    current_quantity=asset.default_quantity
                )
                db.session.add(campaign_asset)
        
        db.session.commit()
        flash(f'Library "{library.name}" imported successfully! Added {len(assets)} assets.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing library: {str(e)}', 'error')
    
    return redirect(url_for('main.campaign_detail', campaign_id=campaign_id))

@main.route('/admin/reports')
@login_required
def reports_dashboard():
    """Reports dashboard showing all available reports"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    # Get all campaigns
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    
    # Check for existing report files
    import os
    reports_dir = '/app/reports'
    report_files = []
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(reports_dir, filename)
                file_stat = os.stat(filepath)
                report_files.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'created': datetime.fromtimestamp(file_stat.st_ctime)
                })
    
    report_files.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('admin/reports.html', 
                         campaigns=campaigns,
                         report_files=report_files)


@main.route('/admin/campaign/<int:campaign_id>/report/view')
@login_required
def view_campaign_report(campaign_id):
    """View detailed campaign report in browser"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Get report data
    campaign_assets = CampaignAsset.query.filter_by(campaign_id=campaign.id).all()
    missions = Mission.query.filter_by(campaign_id=campaign.id).order_by(Mission.mission_date).all()
    
    # Calculate statistics
    total_initial = sum(ca.initial_quantity for ca in campaign_assets)
    total_current = sum(ca.current_quantity for ca in campaign_assets)
    total_change = total_current - total_initial
    
    # Asset statistics by type
    asset_types = {}
    for ca in campaign_assets:
        asset_type = ca.asset.type
        if asset_type not in asset_types:
            asset_types[asset_type] = {
                'count': 0,
                'initial': 0,
                'current': 0,
                'assets': []
            }
        asset_types[asset_type]['count'] += 1
        asset_types[asset_type]['initial'] += ca.initial_quantity
        asset_types[asset_type]['current'] += ca.current_quantity
        asset_types[asset_type]['assets'].append(ca)
    
    # Mission statistics
    mission_stats = {
        'total': len(missions),
        'completed': len([m for m in missions if m.status == 'completed']),
        'in_progress': len([m for m in missions if m.status == 'in_progress']),
        'planned': len([m for m in missions if m.status == 'planned']),
        'cancelled': len([m for m in missions if m.status == 'cancelled'])
    }
    
    # Event statistics
    total_events = 0
    event_types = {}
    total_asset_changes = 0
    
    for mission in missions:
        total_events += len(mission.events)
        for event in mission.events:
            event_type = event.event_type
            event_types[event_type] = event_types.get(event_type, 0) + 1
            total_asset_changes += len(event.asset_changes)
    
    return render_template('admin/report_view.html',
                         campaign=campaign,
                         campaign_assets=campaign_assets,
                         missions=missions,
                         total_initial=total_initial,
                         total_current=total_current,
                         total_change=total_change,
                         asset_types=asset_types,
                         mission_stats=mission_stats,
                         total_events=total_events,
                         event_types=event_types,
                         total_asset_changes=total_asset_changes)


@main.route('/admin/campaign/<int:campaign_id>/report/download/<format>')
@login_required
def download_campaign_report(campaign_id, format):
    """Download campaign report in various formats"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    if format == 'csv':
        return generate_campaign_report(campaign_id)
    
    elif format == 'json':
        report_data = generate_final_report(campaign)
        
        response = make_response(json.dumps(report_data, indent=2))
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_report.json'
        response.headers['Content-type'] = 'application/json'
        return response
    
    else:
        flash('Invalid report format', 'error')
        return redirect(url_for('main.reports_dashboard'))


@main.route('/admin/reports/download/<filename>')
@login_required
def download_report_file(filename):
    """Download a saved report file"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    reports_dir = os.path.abspath('/app/reports')
    filepath = os.path.abspath(os.path.join(reports_dir, filename))
    
    # Ensure the resolved path is within the reports directory to prevent path traversal
    if not filepath.startswith(reports_dir + os.sep) and filepath != reports_dir:
        flash('Report file not found', 'error')
        return redirect(url_for('main.reports_dashboard'))
    
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash('Report file not found', 'error')
        return redirect(url_for('main.reports_dashboard'))

@main.route('/admin/libraries/<int:library_id>/import-assets', methods=['POST'])
@login_required
def import_assets_to_library(library_id):
    """Import assets from other libraries to this library"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.manage_libraries'))
    
    try:
        library = AssetLibrary.query.get_or_404(library_id)
        asset_ids = request.form.getlist('asset_ids')
        
        if not asset_ids:
            flash('No assets selected for import.', 'warning')
            return redirect(url_for('main.library_detail', library_id=library_id))
        
        imported_count = 0
        skipped_count = 0
        
        for asset_id in asset_ids:
            source_asset = Asset.query.get(asset_id)
            if not source_asset:
                continue
            
            # Check if asset with same name already exists in this library
            existing = Asset.query.filter_by(
                library_id=library_id,
                name=source_asset.name
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create a copy of the asset in this library
            new_asset = Asset(
                library_id=library_id,
                name=source_asset.name,
                type=source_asset.type,
                category=source_asset.category,
                description=source_asset.description,
                default_quantity=source_asset.default_quantity,
                is_unique=source_asset.is_unique,
                show_in_public=source_asset.show_in_public
            )
            
            db.session.add(new_asset)
            imported_count += 1
        
        db.session.commit()
        
        if imported_count > 0:
            flash(f'Successfully imported {imported_count} asset(s) to "{library.name}".', 'success')
        if skipped_count > 0:
            flash(f'Skipped {skipped_count} asset(s) - already exist in this library.', 'warning')
        
        return redirect(url_for('main.library_detail', library_id=library_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing assets: {str(e)}', 'error')
        return redirect(url_for('main.library_detail', library_id=library_id))

@main.route('/manager')
@login_required
def manager_dashboard():
    """Manager Dashboard - Limited to active campaign only"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    # Redirect admins to their dashboard
    if current_user.is_admin:
        return redirect(url_for('main.admin_dashboard'))
    
    # Get active campaign
    active_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    
    if not active_campaign:
        return render_template('manager/dashboard.html', 
                             campaign=None,
                             missions=[],
                             recent_events=[],
                             asset_summary={})
    
    # Get campaign assets
    campaign_assets = CampaignAsset.query.filter_by(campaign_id=active_campaign.id).all()
    
    # Get missions
    missions = Mission.query.filter_by(campaign_id=active_campaign.id).order_by(Mission.mission_date.desc()).limit(5).all()
    
    # Get recent events
    recent_events = []
    for mission in Mission.query.filter_by(campaign_id=active_campaign.id).all():
        for event in mission.events:
            recent_events.append({
                'mission': mission.name,
                'title': event.title,
                'date': event.event_date,
                'type': event.event_type
            })
    recent_events.sort(key=lambda x: x['date'], reverse=True)
    recent_events = recent_events[:10]
    
    # Asset summary
    asset_summary = {
        'total': len(campaign_assets),
        'low_stock': len([ca for ca in campaign_assets if ca.current_quantity < 3 and ca.current_quantity > 0]),
        'depleted': len([ca for ca in campaign_assets if ca.current_quantity == 0])
    }
    
    return render_template('manager/dashboard.html', 
                         campaign=active_campaign,
                         missions=missions,
                         recent_events=recent_events,
                         asset_summary=asset_summary)


@main.route('/manager/campaign')
@login_required
def manager_campaign():
    """Manager's view of active campaign details"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    if current_user.is_admin:
        return redirect(url_for('main.admin_dashboard'))
    
    active_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    
    if not active_campaign:
        flash('No active campaign found.', 'warning')
        return redirect(url_for('main.manager_dashboard'))
    
    # Get all available libraries
    all_libraries = AssetLibrary.query.order_by(AssetLibrary.name).all()
    
    # Get imported libraries
    imported_library_ids = [imp.library_id for imp in active_campaign.imported_libraries]
    imported_libraries = AssetLibrary.query.filter(AssetLibrary.id.in_(imported_library_ids)).all() if imported_library_ids else []
    
    # Get assets in campaign grouped by library
    campaign_assets = CampaignAsset.query.filter_by(campaign_id=active_campaign.id).all()
    assets_by_library = {}
    for ca in campaign_assets:
        lib_name = ca.library.name
        if lib_name not in assets_by_library:
            assets_by_library[lib_name] = []
        assets_by_library[lib_name].append(ca)
    
    return render_template('manager/campaign.html',
                         campaign=active_campaign,
                         all_libraries=all_libraries,
                         imported_libraries=imported_libraries,
                         imported_library_ids=imported_library_ids,
                         campaign_assets=campaign_assets,
                         assets_by_library=assets_by_library)


@main.route('/manager/missions')
@login_required
def manager_missions():
    """Manager's view of missions in active campaign"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    if current_user.is_admin:
        return redirect(url_for('main.admin_dashboard'))
    
    active_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    
    if not active_campaign:
        flash('No active campaign found.', 'warning')
        return redirect(url_for('main.manager_dashboard'))
    
    missions = Mission.query.filter_by(campaign_id=active_campaign.id).order_by(Mission.order_index).all()
    
    # Get max order index for new mission
    max_order = db.session.query(db.func.max(Mission.order_index)).filter_by(
        campaign_id=active_campaign.id
    ).scalar() or 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('manager/missions.html', 
                         campaign=active_campaign, 
                         missions=missions,
                         max_order=max_order,
                         today=today)

@main.route('/admin/switch-to-manager-view')
@login_required
def switch_to_manager_view():
    """Allow admins to temporarily view as manager for testing"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    # Store in session that admin is testing manager view
    session['test_manager_view'] = True
    flash('Switched to Manager View (Testing Mode)', 'info')
    return redirect(url_for('main.manager_dashboard'))


@main.route('/admin/switch-to-admin-view')
@login_required
def switch_to_admin_view():
    """Return to admin view from manager testing mode"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    session.pop('test_manager_view', None)
    flash('Returned to Admin View', 'success')
    return redirect(url_for('main.admin_dashboard'))

# User Management Routes (Admin Only)
@main.route('/admin/users')
@login_required
def manage_users():
    """Manage users - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)


@main.route('/admin/users/create', methods=['POST'])
@login_required
def create_user():
    """Create a new user - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    try:
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'public')
        
        # Check if username already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash(f'Username "{username}" already exists!', 'error')
            return redirect(url_for('main.manage_users'))
        
        user = User(username=username)
        user.set_password(password)
        
        if role == 'admin':
            user.is_admin = True
            user.is_manager = True
        elif role == 'manager':
            user.is_admin = False
            user.is_manager = True
        else:
            user.is_admin = False
            user.is_manager = False
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User "{username}" created successfully as {role.upper()}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_users'))


@main.route('/admin/users/edit', methods=['POST'])
@login_required
def edit_user():
    """Edit user role - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    try:
        user_id = request.form['user_id']
        user = User.query.get_or_404(user_id)
        
        # Prevent admin from removing their own admin rights
        if user.id == current_user.id and request.form.get('role') != 'admin':
            flash('You cannot remove your own admin privileges!', 'error')
            return redirect(url_for('main.manage_users'))
        
        role = request.form.get('role', 'public')
        
        if role == 'admin':
            user.is_admin = True
            user.is_manager = True
        elif role == 'manager':
            user.is_admin = False
            user.is_manager = True
        else:
            user.is_admin = False
            user.is_manager = False
        
        db.session.commit()
        flash(f'User "{user.username}" updated to {role.upper()}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_users'))


@main.route('/admin/users/delete', methods=['POST'])
@login_required
def delete_user():
    """Delete a user - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    try:
        user_id = request.form['user_id']
        user = User.query.get_or_404(user_id)
        
        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            flash('You cannot delete your own account!', 'error')
            return redirect(url_for('main.manage_users'))
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User "{username}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_users'))


@main.route('/admin/users/reset-password', methods=['POST'])
@login_required
def reset_user_password():
    """Reset user password - ADMIN ONLY"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.admin_dashboard'))
    
    try:
        user_id = request.form['user_id']
        user = User.query.get_or_404(user_id)
        new_password = request.form['new_password']
        
        user.set_password(new_password)
        db.session.commit()
        
        flash(f'Password for "{user.username}" has been reset!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
    
    return redirect(url_for('main.manage_users'))


# User Profile Routes (All Users)
@main.route('/profile')
@login_required
def user_profile():
    """User profile and settings"""
    return render_template('profile.html', user=current_user)


@main.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        new_username = request.form.get('username', '').strip()
        
        if new_username and new_username != current_user.username:
            # Check if username is already taken
            existing = User.query.filter_by(username=new_username).first()
            if existing:
                flash('Username already taken!', 'error')
                return redirect(url_for('main.user_profile'))
            
            current_user.username = new_username
            db.session.commit()
            flash('Username updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}', 'error')
    
    return redirect(url_for('main.user_profile'))


@main.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect!', 'error')
            return redirect(url_for('main.user_profile'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match!', 'error')
            return redirect(url_for('main.user_profile'))
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return redirect(url_for('main.user_profile'))
        
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error changing password: {str(e)}', 'error')
    
    return redirect(url_for('main.user_profile'))