from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, send_file, make_response
from flask_login import login_required, current_user
from app import db
from app.models import Campaign, Asset, CampaignLibrary, Mission, Event, AssetChange, Log, User
from datetime import datetime
import json
import csv
import io
from datetime import datetime

main = Blueprint('main', __name__)

# Public routes
@main.route('/')
def index():
    current_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    if current_campaign:
        assets = CampaignLibrary.query.filter_by(campaign_id=current_campaign.id).all()
        asset_list = [{
            'name': lib.asset.name,
            'type': lib.asset.type,
            'category': lib.asset.category,
            'current_quantity': lib.current_quantity
        } for lib in assets]
    else:
        asset_list = []
    
    return render_template('public/dashboard.html', 
                         campaign=current_campaign, 
                         assets=asset_list)

@main.route('/api/current-pool')
def current_pool():
    current_campaign = Campaign.query.filter_by(is_active=True, is_closed=False).first()
    if not current_campaign:
        return jsonify([])
    
    assets = CampaignLibrary.query.filter_by(campaign_id=current_campaign.id).all()
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
    if not current_user.is_manager:
        return redirect(url_for('main.index'))
    
    campaigns = Campaign.query.all()
    return render_template('admin/dashboard.html', campaigns=campaigns)

# Mission Management Routes
@main.route('/admin/campaign/<int:campaign_id>/missions')
@login_required
def campaign_missions(campaign_id):
    """View and manage missions for a campaign"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    campaign = Campaign.query.get_or_404(campaign_id)
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
            order_index=order_index
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
    campaign_assets = CampaignLibrary.query.filter_by(
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
                    
                    # Update campaign library quantity
                    lib = CampaignLibrary.query.filter_by(
                        campaign_id=campaign_id,
                        asset_id=asset_id
                    ).first()
                    
                    if lib:
                        lib.current_quantity += quantity_change
                        if lib.current_quantity < 0:
                            lib.current_quantity = 0
                    
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
            # Find the campaign library entry and revert the change
            lib = CampaignLibrary.query.filter_by(
                campaign_id=event.mission.campaign_id,
                asset_id=change.asset_id
            ).first()
            
            if lib:
                lib.current_quantity -= change.quantity_change
                if lib.current_quantity < 0:
                    lib.current_quantity = 0
        
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
        return jsonify({'error': 'Unauthorized'}), 403
    
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
        
        # Update campaign library quantity
        lib = CampaignLibrary.query.filter_by(
            campaign_id=event.mission.campaign_id,
            asset_id=asset_change.asset_id
        ).first()
        
        if lib:
            lib.current_quantity += asset_change.quantity_change
            if lib.current_quantity < 0:
                lib.current_quantity = 0
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

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
        
        # Revert the asset change in campaign library
        lib = CampaignLibrary.query.filter_by(
            campaign_id=event.mission.campaign_id,
            asset_id=change.asset_id
        ).first()
        
        if lib:
            lib.current_quantity -= change.quantity_change
            if lib.current_quantity < 0:
                lib.current_quantity = 0
        
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
    libraries = CampaignLibrary.query.filter_by(campaign_id=campaign.id).all()
    missions = Mission.query.filter_by(campaign_id=campaign.id).all()
    
    asset_history = []
    for lib in libraries:
        asset_history.append({
            'asset_name': lib.asset.name,
            'asset_type': lib.asset.type,
            'initial_quantity': lib.initial_quantity,
            'current_quantity': lib.current_quantity,
            'net_change': lib.current_quantity - lib.initial_quantity
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
        campaigns_using = CampaignLibrary.query.filter_by(asset_id=asset_id).count()
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
    """Manage campaigns"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # If set_active checkbox is checked, deactivate all campaigns first
            if request.form.get('set_active') == 'on':
                Campaign.query.update({'is_active': False})
                is_active = True
            else:
                is_active = False
            
            campaign = Campaign(
                name=request.form['name'],
                description=request.form.get('description', ''),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d'),
                is_active=is_active
            )
            db.session.add(campaign)
            db.session.commit()
            
            flash(f'Campaign "{campaign.name}" created successfully!', 'success')
        except Exception as e:
            flash(f'Error creating campaign: {str(e)}', 'error')
        
        return redirect(url_for('main.manage_campaigns'))
    
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('admin/campaigns.html', campaigns=campaigns, today=today)

@main.route('/admin/campaign/set-active', methods=['POST'])
@login_required
def set_campaign_active():
    """Set a campaign as active"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        campaign_id = request.form['campaign_id']
        
        # Deactivate all campaigns
        Campaign.query.update({'is_active': False})
        
        # Activate selected campaign
        campaign = Campaign.query.get_or_404(campaign_id)
        campaign.is_active = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Campaign "{campaign.name}" is now active'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@main.route('/admin/campaign/close', methods=['POST'])
@login_required
def close_campaign():
    """Close a campaign"""
    if not current_user.is_manager:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        campaign_id = request.form['campaign_id']
        campaign = Campaign.query.get_or_404(campaign_id)
        
        if campaign.is_closed:
            return jsonify({'success': False, 'error': 'Campaign already closed'}), 400
        
        campaign.is_closed = True
        campaign.is_active = False
        campaign.end_date = datetime.utcnow()
        
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
        
        return jsonify({
            'success': True,
            'message': f'Campaign "{campaign.name}" closed successfully',
            'report': report_filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@main.route('/admin/campaign/<int:campaign_id>')
@login_required
def campaign_detail(campaign_id):
    """View and manage a specific campaign"""
    if not current_user.is_manager:
        flash('Access denied. Manager login required.', 'error')
        return redirect(url_for('main.index'))
    
    campaign = Campaign.query.get_or_404(campaign_id)
    assets = Asset.query.order_by(Asset.name).all()
    
    # Get assets already in this campaign
    campaign_assets = CampaignLibrary.query.filter_by(campaign_id=campaign_id).all()
    campaign_asset_ids = [ca.asset_id for ca in campaign_assets]
    
    return render_template('admin/campaign_detail.html',
                         campaign=campaign,
                         assets=assets,
                         campaign_assets=campaign_assets,
                         campaign_asset_ids=campaign_asset_ids)

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
        existing = CampaignLibrary.query.filter_by(
            campaign_id=campaign_id,
            asset_id=asset_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Asset already in campaign'}), 400
        
        # Add asset to campaign
        campaign_library = CampaignLibrary(
            campaign_id=campaign_id,
            asset_id=asset_id,
            initial_quantity=quantity,
            current_quantity=quantity
        )
        
        db.session.add(campaign_library)
        db.session.commit()
        
        return jsonify({'success': True, 'id': campaign_library.id})
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
        
        campaign_lib = CampaignLibrary.query.get_or_404(library_id)
        
        # Update both initial and current quantities
        diff = quantity - campaign_lib.initial_quantity
        campaign_lib.initial_quantity = quantity
        campaign_lib.current_quantity += diff
        
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
        
        campaign_lib = CampaignLibrary.query.get_or_404(library_id)
        db.session.delete(campaign_lib)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400