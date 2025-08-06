#!/usr/bin/env python3
"""
Website Review Tool - Multi-user Crowdsourced Version
Designed for Vercel deployment with concurrent user support
"""

import csv
import json
import os
import uuid
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file, session
from storage import get_storage_backend

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Configuration
CSV_FILE = 'b2c_failures_review.csv'
STATE_FILE = 'shared_state.json'
LIKED_CSV = 'liked_websites.csv'
DISLIKED_CSV = 'disliked_websites.csv'
USER_SESSION_TIMEOUT = 300  # 5 minutes timeout for inactive sessions

# Thread lock for concurrent access
state_lock = threading.Lock()

class MultiUserWebsiteReviewer:
    def __init__(self):
        self.companies = []
        self.storage = get_storage_backend()
        self.shared_state = {
            'global_index': 0,
            'assigned_companies': {},  # {company_index: {'user_id': str, 'assigned_at': timestamp}}
            'completed_reviews': {
                'liked': [],
                'disliked': []
            },
            'user_sessions': {},  # {user_id: {'last_active': timestamp, 'current_company': index}}
            'last_updated': None
        }
        self.load_data()
        self.load_state()
    
    def load_data(self):
        """Load companies from CSV file"""
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                self.companies = list(reader)
                print(f"Loaded {len(self.companies)} companies")
        except FileNotFoundError:
            print(f"Error: {CSV_FILE} not found")
            self.companies = []
    
    def load_state(self):
        """Load shared state from storage backend"""
        try:
            saved_state = self.storage.load_state()
            if saved_state:
                self.shared_state.update(saved_state)
                print(f"Loaded shared state - Global index: {self.shared_state['global_index']}")
            else:
                print("No existing state found, starting fresh")
        except Exception as e:
            print(f"Error loading state: {e}, starting fresh")
    
    def save_state(self):
        """Save shared state using storage backend"""
        with state_lock:
            self.shared_state['last_updated'] = datetime.now().isoformat()
            success = self.storage.save_state(self.shared_state)
            if not success:
                print("Warning: Failed to save state to storage backend")
    
    def cleanup_expired_sessions(self):
        """Remove expired user sessions and release their assigned companies"""
        current_time = time.time()
        expired_users = []
        
        # Find expired sessions
        for user_id, session_data in self.shared_state['user_sessions'].items():
            if current_time - session_data['last_active'] > USER_SESSION_TIMEOUT:
                expired_users.append(user_id)
        
        # Clean up expired sessions
        for user_id in expired_users:
            self.release_user_assignments(user_id)
            del self.shared_state['user_sessions'][user_id]
            print(f"Cleaned up expired session for user {user_id}")
    
    def release_user_assignments(self, user_id):
        """Release all companies assigned to a specific user"""
        assignments_to_remove = []
        for company_index, assignment in self.shared_state['assigned_companies'].items():
            if assignment['user_id'] == user_id:
                assignments_to_remove.append(company_index)
        
        for company_index in assignments_to_remove:
            del self.shared_state['assigned_companies'][str(company_index)]
    
    def get_user_id(self):
        """Get or create user ID from session"""
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        return session['user_id']
    
    def update_user_activity(self, user_id):
        """Update user's last activity timestamp"""
        current_time = time.time()
        if user_id not in self.shared_state['user_sessions']:
            self.shared_state['user_sessions'][user_id] = {
                'last_active': current_time,
                'current_company': None
            }
        else:
            self.shared_state['user_sessions'][user_id]['last_active'] = current_time
    
    def get_next_available_company(self, user_id):
        """Get the next available company for a user"""
        with state_lock:
            self.cleanup_expired_sessions()
            self.update_user_activity(user_id)
            
            # Check if user already has an assigned company
            for company_index, assignment in self.shared_state['assigned_companies'].items():
                if assignment['user_id'] == user_id:
                    company_idx = int(company_index)
                    if company_idx < len(self.companies):
                        return self.companies[company_idx], company_idx
            
            # Find next unassigned company
            while self.shared_state['global_index'] < len(self.companies):
                current_index = self.shared_state['global_index']
                
                # Check if this company is already assigned
                if str(current_index) not in self.shared_state['assigned_companies']:
                    # Assign to current user
                    self.shared_state['assigned_companies'][str(current_index)] = {
                        'user_id': user_id,
                        'assigned_at': time.time()
                    }
                    self.shared_state['user_sessions'][user_id]['current_company'] = current_index
                    self.save_state()
                    return self.companies[current_index], current_index
                
                self.shared_state['global_index'] += 1
            
            return None, None
    
    def mark_company_reviewed(self, user_id, company_index, liked):
        """Mark a company as reviewed and remove assignment"""
        with state_lock:
            if company_index >= len(self.companies):
                return False
            
            # Verify user owns this assignment
            assignment = self.shared_state['assigned_companies'].get(str(company_index))
            if not assignment or assignment['user_id'] != user_id:
                return False
            
            company = self.companies[company_index]
            
            # Add review to completed reviews
            if liked:
                self.shared_state['completed_reviews']['liked'].append(company)
            else:
                self.shared_state['completed_reviews']['disliked'].append(company)
            
            # Remove assignment
            del self.shared_state['assigned_companies'][str(company_index)]
            
            # Update user session
            if user_id in self.shared_state['user_sessions']:
                self.shared_state['user_sessions'][user_id]['current_company'] = None
            
            # Advance global index if this was the next expected company
            if company_index == self.shared_state['global_index']:
                self.shared_state['global_index'] += 1
            
            self.save_state()
            return True
    
    def get_progress_stats(self):
        """Get overall progress statistics"""
        total_companies = len(self.companies)
        completed = len(self.shared_state['completed_reviews']['liked']) + len(self.shared_state['completed_reviews']['disliked'])
        assigned = len(self.shared_state['assigned_companies'])
        active_users = len([u for u in self.shared_state['user_sessions'].values() 
                           if time.time() - u['last_active'] < USER_SESSION_TIMEOUT])
        
        return {
            'total': total_companies,
            'completed': completed,
            'assigned': assigned,
            'remaining': total_companies - completed - assigned,
            'liked_count': len(self.shared_state['completed_reviews']['liked']),
            'disliked_count': len(self.shared_state['completed_reviews']['disliked']),
            'active_users': active_users,
            'progress_percent': round((completed / total_companies) * 100, 1) if total_companies > 0 else 0
        }
    
    def export_results(self, category):
        """Export completed reviews to CSV using storage backend"""
        if category not in ['liked', 'disliked']:
            return None
            
        data = self.shared_state['completed_reviews'][category]
        filename = LIKED_CSV if category == 'liked' else DISLIKED_CSV
        
        return self.storage.export_csv(data, filename)
    
    def reset_all_progress(self):
        """Reset all progress (admin function)"""
        with state_lock:
            self.shared_state = {
                'global_index': 0,
                'assigned_companies': {},
                'completed_reviews': {'liked': [], 'disliked': []},
                'user_sessions': {},
                'last_updated': datetime.now().isoformat()
            }
            self.save_state()

# Initialize the global reviewer instance
reviewer = MultiUserWebsiteReviewer()

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
    user_id = reviewer.get_user_id()
    company, company_index = reviewer.get_next_available_company(user_id)
    progress = reviewer.get_progress_stats()
    
    if company is None:
        return jsonify({
            'finished': True,
            'progress': progress
        })
    
    return jsonify({
        'finished': False,
        'company': company,
        'company_index': company_index,
        'progress': progress,
        'user_id': user_id[:8]  # Show partial user ID for debugging
    })

@app.route('/api/mark', methods=['POST'])
def mark_company():
    """Mark current company as liked or disliked"""
    data = request.get_json()
    liked = data.get('liked', False)
    company_index = data.get('company_index')
    
    if company_index is None:
        return jsonify({'success': False, 'error': 'No company index provided'})
    
    user_id = reviewer.get_user_id()
    success = reviewer.mark_company_reviewed(user_id, company_index, liked)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Unable to mark company - assignment may have expired'})

@app.route('/api/progress')
def get_progress():
    """Get current progress statistics"""
    return jsonify(reviewer.get_progress_stats())

@app.route('/api/export/<category>')
def export_csv(category):
    """Export liked or disliked companies"""
    if category not in ['liked', 'disliked']:
        return jsonify({'error': 'Invalid category'}), 400
    
    filename = reviewer.export_results(category)
    
    if filename is None:
        return jsonify({'error': f'No {category} companies to export'}), 400
    
    return send_file(filename, as_attachment=True, 
                    download_name=f'{category}_websites_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

@app.route('/api/admin/reset', methods=['POST'])
def admin_reset():
    """Reset all progress (admin only)"""
    # In production, add proper admin authentication here
    reviewer.reset_all_progress()
    return jsonify({'success': True, 'message': 'All progress reset successfully'})

@app.route('/api/admin/stats')
def admin_stats():
    """Get detailed admin statistics"""
    stats = reviewer.get_progress_stats()
    stats['detailed'] = {
        'assigned_companies': len(reviewer.shared_state['assigned_companies']),
        'active_sessions': list(reviewer.shared_state['user_sessions'].keys()),
        'last_updated': reviewer.shared_state.get('last_updated'),
        'global_index': reviewer.shared_state['global_index']
    }
    return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)