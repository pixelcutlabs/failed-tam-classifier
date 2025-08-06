# Setup Persistent Storage for Review Data

To prevent losing your review data when deploying new versions, we need to set up GitHub Gist as persistent storage.

## Step 1: Create a GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "Website Review Tool"
4. Select these scopes:
   - ✅ `gist` (Create and modify gists)
5. Click "Generate token"
6. **SAVE THE TOKEN** - you won't see it again!

## Step 2: Create a GitHub Gist

1. Go to https://gist.github.com/
2. Click "Create a new gist"
3. Filename: `review_state.json`
4. Content: `{"shared_state": {"global_index": 0, "assigned_companies": {}, "completed_reviews": {"liked": [], "disliked": []}, "user_sessions": {}, "leaderboard": {}, "last_updated": null}, "version": "1.1"}`
5. Create as **Secret gist** (recommended)
6. Click "Create secret gist"
7. **SAVE THE GIST ID** from the URL (e.g., if URL is `https://gist.github.com/username/abc123def456`, the ID is `abc123def456`)

## Step 3: Set Vercel Environment Variables

1. Go to your Vercel dashboard
2. Select your project → Settings → Environment Variables
3. Add these variables:

```
GITHUB_TOKEN = your_personal_access_token_here
GITHUB_GIST_ID = your_gist_id_here
```

4. Click "Save" for each

## Step 4: Redeploy

After setting the environment variables, redeploy your app:
- Either push a new commit to GitHub
- Or manually redeploy from Vercel dashboard

## How It Works

- **Local Storage**: Fast access during the same deployment
- **GitHub Gist**: Persistent storage that survives deployments
- **Auto-Recovery**: On new deployments, loads from GitHub Gist automatically
- **Dual-Save**: Every review saves to both local and GitHub for reliability

## Benefits

✅ **Review data persists across deployments**  
✅ **Leaderboard and usernames preserved**  
✅ **Fast local access during same deployment**  
✅ **Automatic recovery on new deployments**  
✅ **Free solution using GitHub**

## Troubleshooting

If data still resets:
1. Check Vercel environment variables are set correctly
2. Check GitHub token has `gist` permission
3. Check gist exists and is accessible
4. Look at server logs for GitHub API errors

The system will gracefully fall back to `/tmp` storage if GitHub is not configured.