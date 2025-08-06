# Deployment Guide - Website Review Tool

## 🚀 Deploy to Vercel (Recommended)

This application is optimized for Vercel deployment with multi-user crowdsourcing support.

### Prerequisites

1. **GitHub Account**: Your code needs to be in a GitHub repository
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
3. **Git**: Ensure your code is committed to Git

### Step 1: Prepare Your Repository

1. **Initialize Git Repository** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Website Review Tool"
   ```

2. **Create GitHub Repository**:
   - Go to [GitHub](https://github.com) and create a new repository
   - Push your code:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy to Vercel

1. **Connect GitHub to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Sign in with GitHub
   - Click "New Project"
   - Import your repository

2. **Configure Environment Variables**:
   In Vercel dashboard, go to Settings → Environment Variables and add:
   ```
   SECRET_KEY=your-super-secret-key-here-change-this
   ```

3. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be available at `https://your-project-name.vercel.app`

### Step 3: Share with Your Team

Your crowdsourced website review tool is now live! Share these URLs:

- **Review Interface**: `https://your-project-name.vercel.app/`
- **Admin Dashboard**: `https://your-project-name.vercel.app/admin`

## 🔧 Local Development

### Setup
```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run locally
python3 app.py
```

### URLs
- Main Interface: http://localhost:5001
- Admin Dashboard: http://localhost:5001/admin

## 📊 Multi-User Features

### How It Works
1. **Automatic User Sessions**: Each user gets a unique session ID
2. **No Duplicates**: System ensures no two users review the same website
3. **Progress Tracking**: Real-time progress visible to all users
4. **Auto-Cleanup**: Inactive sessions automatically released after 5 minutes

### User Experience
- Users visit the public URL and immediately start reviewing
- Each user sees different websites (no coordination needed)
- Progress is shared and visible to everyone
- Admin can export results anytime

## 🎯 Production Considerations

### Current Storage
- **Development**: Uses local JSON files
- **Vercel**: Uses in-memory storage (resets on deployment)

### For High-Volume Production

If you need persistent storage for large teams, implement cloud storage in `storage.py`:

#### Option 1: Redis/Upstash (Recommended for Vercel)
```python
# Add to requirements.txt
redis>=4.0.0

# Update storage.py CloudStorage class
import redis
def load_state(self):
    r = redis.from_url(os.environ['REDIS_URL'])
    state = r.get('review_state')
    return json.loads(state) if state else {}
```

#### Option 2: PostgreSQL/PlanetScale
```python
# Add to requirements.txt  
psycopg2-binary>=2.9.0

# Implement database storage in storage.py
```

#### Option 3: AWS S3 + DynamoDB
```python
# Add to requirements.txt
boto3>=1.26.0

# Implement AWS storage in storage.py
```

### Environment Variables for Production

Add these to Vercel Environment Variables:

```bash
# Required
SECRET_KEY=your-super-secret-key-256-bits-long

# Optional - for cloud storage
REDIS_URL=redis://username:password@hostname:port
DATABASE_URL=postgresql://username:password@hostname:port/database
STORAGE_URL=s3://your-bucket-name
```

## 🔐 Security Considerations

### Admin Access
- Currently, admin dashboard is publicly accessible
- For production, add authentication:

```python
@app.route('/admin')
def admin():
    # Add authentication check here
    if not is_authenticated():
        return redirect('/login')
    return render_template('admin.html')
```

### Rate Limiting
Consider adding rate limiting for production:

```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/mark', methods=['POST'])
@limiter.limit("60 per minute")
def mark_company():
    # existing code
```

## 📈 Monitoring & Analytics

### Built-in Analytics
- Real-time user count
- Progress tracking
- Completion statistics

### Add External Monitoring
```python
# Add to requirements.txt
sentry-sdk[flask]>=1.0.0

# Add to app.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[FlaskIntegration()]
)
```

## 🚨 Troubleshooting

### Common Issues

1. **CSV File Not Found**
   - Ensure `b2c_failures_review.csv` is in the repository
   - Check file name spelling

2. **Users Getting Same Websites**
   - Clear browser cookies/sessions
   - Check server logs for errors

3. **Progress Not Saving**
   - Verify storage backend is working
   - Check Vercel function logs

4. **Deployment Fails**
   - Verify `vercel.json` configuration
   - Check Python version compatibility

### Vercel Logs
```bash
# Install Vercel CLI
npm i -g vercel

# View logs
vercel logs
```

## 🎉 You're Ready!

Your crowdsourced website review tool is now ready for your team to use. The system will handle multiple users automatically and ensure efficient, duplicate-free reviewing.

**Next Steps**:
1. Share the URL with your team
2. Monitor progress via the admin dashboard  
3. Export results when complete
4. Consider adding cloud storage for persistence (optional)

Happy reviewing! 🚀