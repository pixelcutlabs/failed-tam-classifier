#!/usr/bin/env python3
"""
Website Review Tool - Vercel Serverless Function
"""

import csv
import json
import os
import uuid
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, session
from flask_cors import CORS
import io
import tempfile

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Enable CORS for all routes
CORS(app)

# Configuration
USER_SESSION_TIMEOUT = 120  # 2 minutes timeout for inactive sessions (reduced for better multi-user experience)

# State file path (using /tmp for Vercel)
STATE_FILE = '/tmp/review_state.json'

# Global state (persistent storage for Vercel)
global_state = {
    'companies': [],
    'shared_state': {
        'global_index': 0,
        'assigned_companies': {},
        'completed_reviews': {'liked': [], 'disliked': []},
        'user_sessions': {},
        'leaderboard': {},  # {username: {'reviews': count, 'liked': count, 'disliked': count, 'last_active': timestamp}}
        'last_updated': None
    }
}

def save_state():
    """Save current state to persistent storage"""
    try:
        # Save to /tmp which persists across requests in Vercel
        with open(STATE_FILE, 'w') as f:
            # Don't save companies data (too large), just shared state
            state_to_save = {
                'shared_state': global_state['shared_state'],
                'version': '1.0',  # For future compatibility
                'saved_at': datetime.now().isoformat()
            }
            json.dump(state_to_save, f, indent=2)
        print(f"State saved to {STATE_FILE}")
    except Exception as e:
        print(f"Error saving state: {e}")

def clear_state():
    """Clear persistent state file"""
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print(f"State file {STATE_FILE} cleared")
    except Exception as e:
        print(f"Error clearing state: {e}")

def load_state():
    """Load state from persistent storage"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                saved_state = json.load(f)
                global_state['shared_state'].update(saved_state['shared_state'])
            print(f"State loaded from {STATE_FILE}")
            print(f"Loaded progress: {len(global_state['shared_state']['completed_reviews']['liked'])} liked, {len(global_state['shared_state']['completed_reviews']['disliked'])} disliked")
            return True
    except Exception as e:
        print(f"Error loading state: {e}")
    return False

def load_companies():
    """Load companies from CSV - for Vercel, we'll embed the data"""
    if global_state['companies']:
        return global_state['companies']
    
    # Try to load from file (local development)
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'b2c_failures_review.csv')
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                global_state['companies'] = list(reader)
                print(f"Loaded {len(global_state['companies'])} companies from file")
                return global_state['companies']
        except Exception as e:
            print(f"Error loading CSV: {e}")
    
    # Fallback: Sample data for demo
    global_state['companies'] = [
        {
            'company_name': 'Sample Company 1',
            'website': 'https://example.com',
            'country': 'United States',
            'employee_count': '100',
            'industry': 'Technology',
            'travel_category': '',
            'page_title': 'Sample Company 1',
            'b2c_score': 'Unknown',
            'b2c_reasoning': 'Demo data',
            'source_file': 'demo',
            'line_number': '1'
        },
        {
            'company_name': 'Sample Company 2', 
            'website': 'https://google.com',
            'country': 'United States',
            'employee_count': '50',
            'industry': 'Technology',
            'travel_category': '',
            'page_title': 'Sample Company 2',
            'b2c_score': 'Unknown',
            'b2c_reasoning': 'Demo data',
            'source_file': 'demo',
            'line_number': '2'
        }
    ]
    print(f"Loaded {len(global_state['companies'])} sample companies for demo")
    return global_state['companies']

def cleanup_expired_sessions():
    """Remove expired user sessions and release their assigned companies"""
    current_time = time.time()
    expired_users = []
    
    for user_id, session_data in global_state['shared_state']['user_sessions'].items():
        if current_time - session_data['last_active'] > USER_SESSION_TIMEOUT:
            expired_users.append(user_id)
    
    for user_id in expired_users:
        release_user_assignments(user_id)
        del global_state['shared_state']['user_sessions'][user_id]

def release_user_assignments(user_id):
    """Release all companies assigned to a specific user"""
    assignments_to_remove = []
    for company_index, assignment in global_state['shared_state']['assigned_companies'].items():
        if assignment['user_id'] == user_id:
            assignments_to_remove.append(company_index)
    
    for company_index in assignments_to_remove:
        del global_state['shared_state']['assigned_companies'][str(company_index)]

def get_user_id():
    """Get or create user ID from session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

def get_username():
    """Get username from session or persistent storage"""
    # First try session
    username = session.get('username', None)
    if username:
        return username
    
    # If not in session, try to get from user sessions by user_id
    user_id = get_user_id()
    user_session = global_state['shared_state']['user_sessions'].get(user_id, {})
    return user_session.get('username', None)

def is_username_set():
    """Check if username is set in session or persistent storage"""
    username = get_username()
    return username is not None and username.strip() != ''

def set_username(username):
    """Set username in session and persistent storage"""
    user_id = get_user_id()
    session['username'] = username
    
    # Also store in user sessions for persistence
    if user_id not in global_state['shared_state']['user_sessions']:
        global_state['shared_state']['user_sessions'][user_id] = {
            'last_active': time.time(),
            'current_company': None,
            'username': username
        }
    else:
        global_state['shared_state']['user_sessions'][user_id]['username'] = username
        global_state['shared_state']['user_sessions'][user_id]['last_active'] = time.time()
    
    # Initialize in leaderboard
    if username not in global_state['shared_state']['leaderboard']:
        global_state['shared_state']['leaderboard'][username] = {
            'reviews': 0,
            'liked': 0,
            'disliked': 0,
            'last_active': time.time()
        }
    else:
        # Update last active time for existing user
        global_state['shared_state']['leaderboard'][username]['last_active'] = time.time()
    
    # Save state when username is set/updated
    save_state()

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    current_time = time.time()
    if user_id not in global_state['shared_state']['user_sessions']:
        global_state['shared_state']['user_sessions'][user_id] = {
            'last_active': current_time,
            'current_company': None,
            'username': None  # Will be set when username is provided
        }
    else:
        global_state['shared_state']['user_sessions'][user_id]['last_active'] = current_time

def get_next_available_company(user_id):
    """Get the next available company for a user"""
    companies = load_companies()
    cleanup_expired_sessions()
    update_user_activity(user_id)
    
    # Check if user already has an assigned company
    for company_index, assignment in global_state['shared_state']['assigned_companies'].items():
        if assignment['user_id'] == user_id:
            company_idx = int(company_index)
            if company_idx < len(companies):
                print(f"User {user_id[:8]} returning to existing assignment: {company_idx}")
                return companies[company_idx], company_idx
    
    # Find next unassigned company starting from global_index
    search_index = global_state['shared_state']['global_index']
    max_search = min(search_index + 100, len(companies))  # Limit search to prevent infinite loops
    
    while search_index < max_search:
        # Check if this company is already assigned
        if str(search_index) not in global_state['shared_state']['assigned_companies']:
            # Assign to current user
            global_state['shared_state']['assigned_companies'][str(search_index)] = {
                'user_id': user_id,
                'assigned_at': time.time()
            }
            global_state['shared_state']['user_sessions'][user_id]['current_company'] = search_index
            
            # Only advance global index if we assigned the next expected company
            if search_index == global_state['shared_state']['global_index']:
                global_state['shared_state']['global_index'] += 1
            
            print(f"Assigned company {search_index} to user {user_id[:8]}")
            return companies[search_index], search_index
        
        search_index += 1
    
    # If we couldn't find anything in the immediate range, advance global index and try again
    if global_state['shared_state']['global_index'] < len(companies):
        global_state['shared_state']['global_index'] += 1
        return get_next_available_company(user_id)
    
    print(f"No available companies found for user {user_id[:8]}")
    return None, None

def mark_company_reviewed(user_id, company_index, liked):
    """Mark a company as reviewed and remove assignment"""
    companies = load_companies()
    
    if company_index >= len(companies):
        print(f"❌ Invalid company index {company_index}, max is {len(companies)-1}")
        return False
    
    # Verify user owns this assignment
    assignment = global_state['shared_state']['assigned_companies'].get(str(company_index))
    print(f"🔍 Checking assignment for company {company_index}: {assignment}")
    print(f"🔍 User {user_id[:8]} trying to mark company {company_index}")
    print(f"🔍 Current assignments: {list(global_state['shared_state']['assigned_companies'].keys())}")
    
    if not assignment:
        print(f"❌ No assignment found for company {company_index}")
        # Try to find any assignment for this user
        user_assignments = [idx for idx, assign in global_state['shared_state']['assigned_companies'].items() 
                          if assign['user_id'] == user_id]
        print(f"🔍 User {user_id[:8]} has assignments: {user_assignments}")
        
        # If user has no assignments at all, their session might have been cleaned up
        if not user_assignments:
            print(f"🔄 User {user_id[:8]} has no assignments, session may have expired")
        
        return False
        
    if assignment['user_id'] != user_id:
        print(f"❌ Assignment belongs to {assignment['user_id'][:8]}, not {user_id[:8]}")
        return False
    
    company = companies[company_index]
    
    # Add review to completed reviews
    if liked:
        global_state['shared_state']['completed_reviews']['liked'].append(company)
    else:
        global_state['shared_state']['completed_reviews']['disliked'].append(company)
    
    # Update leaderboard for the user
    username = get_username()
    if username:
        if username in global_state['shared_state']['leaderboard']:
            global_state['shared_state']['leaderboard'][username]['reviews'] += 1
            if liked:
                global_state['shared_state']['leaderboard'][username]['liked'] += 1
            else:
                global_state['shared_state']['leaderboard'][username]['disliked'] += 1
            global_state['shared_state']['leaderboard'][username]['last_active'] = time.time()
    
    # Remove assignment
    del global_state['shared_state']['assigned_companies'][str(company_index)]
    
    # Update user session
    if user_id in global_state['shared_state']['user_sessions']:
        global_state['shared_state']['user_sessions'][user_id]['current_company'] = None
    
    # Advance global index if this was the next expected company
    if company_index == global_state['shared_state']['global_index']:
        global_state['shared_state']['global_index'] += 1
    
    global_state['shared_state']['last_updated'] = datetime.now().isoformat()
    
    # Save state after each review
    save_state()
    
    print(f"Company {company_index} marked as {'liked' if liked else 'disliked'} by user {user_id[:8]}")
    print(f"Total progress: {len(global_state['shared_state']['completed_reviews']['liked'])} liked, {len(global_state['shared_state']['completed_reviews']['disliked'])} disliked")
    
    return True

def get_progress_stats():
    """Get overall progress statistics"""
    companies = load_companies()
    total_companies = len(companies)
    completed = len(global_state['shared_state']['completed_reviews']['liked']) + len(global_state['shared_state']['completed_reviews']['disliked'])
    assigned = len(global_state['shared_state']['assigned_companies'])
    active_users = len([u for u in global_state['shared_state']['user_sessions'].values() 
                       if time.time() - u['last_active'] < USER_SESSION_TIMEOUT])
    
    return {
        'total': total_companies,
        'completed': completed,
        'assigned': assigned,
        'remaining': total_companies - completed - assigned,
        'liked_count': len(global_state['shared_state']['completed_reviews']['liked']),
        'disliked_count': len(global_state['shared_state']['completed_reviews']['disliked']),
        'active_users': active_users,
        'progress_percent': round((completed / total_companies) * 100, 1) if total_companies > 0 else 0
    }

@app.route('/')
def index():
    """Main review interface"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Admin dashboard"""
    return render_template('admin.html')

@app.route('/api/current')
def get_current():
    """Get current company for the user"""
    user_id = get_user_id()
    username = get_username()
    
    print(f"API /current called - User ID: {user_id[:8]}, Username: {username}")
    
    # If no username set, require it
    if not is_username_set():
        print(f"No username set for user {user_id[:8]}, requiring username")
        return jsonify({
            'requires_username': True,
            'progress': get_progress_stats()
        })
    
    company, company_index = get_next_available_company(user_id)
    progress = get_progress_stats()
    
    print(f"User {username} assigned company index: {company_index}")
    
    if company is None:
        return jsonify({
            'finished': True,
            'progress': progress,
            'username': username,
            'user_stats': global_state['shared_state']['leaderboard'].get(username, {})
        })
    
    return jsonify({
        'finished': False,
        'company': company,
        'company_index': company_index,
        'progress': progress,
        'user_id': user_id[:8],
        'username': username,
        'user_stats': global_state['shared_state']['leaderboard'].get(username, {})
    })

@app.route('/api/check-username')
def check_existing_username():
    """Check if user already has a username"""
    username = get_username()
    user_id = get_user_id()
    print(f"Checking username for user {user_id[:8]}: {username}")
    return jsonify({
        'has_username': username is not None,
        'username': username
    })

@app.route('/api/set-username', methods=['POST'])
def set_user_name():
    """Set username for the current session"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'success': False, 'error': 'Username is required'})
    
    # Sanitize username
    username = username[:50]  # Max 50 characters
    
    set_username(username)
    
    return jsonify({
        'success': True,
        'username': username,
        'user_stats': global_state['shared_state']['leaderboard'].get(username, {})
    })

@app.route('/api/mark', methods=['POST'])
def mark_company():
    """Mark current company as liked or disliked"""
    data = request.get_json()
    liked = data.get('liked', False)
    company_index = data.get('company_index')
    
    if company_index is None:
        return jsonify({'success': False, 'error': 'No company index provided'})
    
    user_id = get_user_id()
    success = mark_company_reviewed(user_id, company_index, liked)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Unable to mark company - assignment may have expired'})

@app.route('/api/progress')
def get_progress():
    """Get current progress statistics"""
    return jsonify(get_progress_stats())

@app.route('/api/leaderboard')
def get_leaderboard():
    """Get leaderboard data"""
    leaderboard = global_state['shared_state']['leaderboard']
    
    # Convert to list and sort by review count
    leaderboard_list = []
    for username, stats in leaderboard.items():
        leaderboard_list.append({
            'username': username,
            'reviews': stats['reviews'],
            'liked': stats['liked'],
            'disliked': stats['disliked'],
            'accuracy': round((stats['liked'] / stats['reviews']) * 100, 1) if stats['reviews'] > 0 else 0,
            'last_active': stats['last_active']
        })
    
    # Sort by review count descending
    leaderboard_list.sort(key=lambda x: x['reviews'], reverse=True)
    
    return jsonify({
        'leaderboard': leaderboard_list,
        'total_users': len(leaderboard_list)
    })

@app.route('/api/export/<category>')
def export_csv(category):
    """Export liked or disliked companies"""
    if category not in ['liked', 'disliked']:
        return jsonify({'error': 'Invalid category'}), 400
    
    data = global_state['shared_state']['completed_reviews'][category]
    
    if not data:
        return jsonify({'error': f'No {category} companies to export'}), 400
    
    # Create CSV content
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    # Create response
    csv_content = output.getvalue()
    output.close()
    
    response = app.response_class(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={category}_websites_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )
    
    return response

@app.route('/api/admin/reset', methods=['POST'])
def admin_reset():
    """Reset all progress (admin only)"""
    global_state['shared_state'] = {
        'global_index': 0,
        'assigned_companies': {},
        'completed_reviews': {'liked': [], 'disliked': []},
        'user_sessions': {},
        'leaderboard': {},
        'last_updated': datetime.now().isoformat()
    }
    
    # Save reset state
    save_state()
    
    return jsonify({'success': True, 'message': 'All progress and leaderboard reset successfully'})

@app.route('/api/admin/stats')
def admin_stats():
    """Get detailed admin statistics"""
    stats = get_progress_stats()
    stats['detailed'] = {
        'assigned_companies': len(global_state['shared_state']['assigned_companies']),
        'active_sessions': list(global_state['shared_state']['user_sessions'].keys()),
        'last_updated': global_state['shared_state'].get('last_updated'),
        'global_index': global_state['shared_state']['global_index']
    }
    return jsonify(stats)

@app.route('/api/test')
def test_endpoint():
    """Test endpoint to verify API is working"""
    return jsonify({
        'status': 'success',
        'message': 'API is working!',
        'companies_loaded': len(global_state['companies']),
        'environment': 'vercel' if os.environ.get('VERCEL') else 'local'
    })

@app.route('/api/debug/assignments')
def debug_assignments():
    """Debug endpoint to see current assignments"""
    user_id = get_user_id()
    return jsonify({
        'current_user': user_id[:8],
        'assigned_companies': global_state['shared_state']['assigned_companies'],
        'user_sessions': {uid: {
            'username': data.get('username', 'Unknown'),
            'last_active': data['last_active'],
            'current_company': data.get('current_company', None),
            'time_since_active': time.time() - data['last_active']
        } for uid, data in global_state['shared_state']['user_sessions'].items()},
        'global_index': global_state['shared_state']['global_index'],
        'total_companies': len(global_state['companies']),
        'current_user_assignments': [idx for idx, assign in global_state['shared_state']['assigned_companies'].items() 
                                   if assign['user_id'] == user_id]
    })

# Initialize data on startup
load_companies()
load_state()  # Load persistent state on startup

# Vercel expects the app to be available as 'app'
if __name__ == '__main__':
    app.run(debug=True)