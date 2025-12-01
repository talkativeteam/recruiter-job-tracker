# Push to GitHub - Instructions

Your code is committed locally but needs authentication to push to GitHub. Choose one method:

## Option 1: Use Personal Access Token (Easiest)

### Step 1: Create a Personal Access Token on GitHub
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "recruiter-job-tracker-push")
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token" and **copy it immediately** (you won't see it again)

### Step 2: Push Using Token
```bash
cd "/Users/sidneykennedy/Documents/AI Agents/Scrape Linkedin Jobs - Recruiter Lead Magnet"
git remote set-url origin https://github.com/talkativeteam/recruiter-job-tracker.git
git push -u origin main
```

When prompted for password, **paste your personal access token** (not your GitHub password).

---

## Option 2: Use SSH Keys (More Secure)

### Step 1: Check for existing SSH keys
```bash
ls -la ~/.ssh/
```

If you see `id_ed25519` or `id_rsa`, you have keys. Skip to Step 3.

### Step 2: Generate SSH keys (if needed)
```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press Enter for all prompts (use defaults)
```

### Step 3: Add SSH key to GitHub
1. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
2. Go to https://github.com/settings/ssh/new
3. Title: "MacBook"
4. Paste the key
5. Click "Add SSH key"

### Step 4: Push to GitHub
```bash
cd "/Users/sidneykennedy/Documents/AI Agents/Scrape Linkedin Jobs - Recruiter Lead Magnet"
git remote set-url origin git@github.com:talkativeteam/recruiter-job-tracker.git
git push -u origin main
```

---

## Verify Push Succeeded

After pushing, verify on GitHub:
- Go to https://github.com/talkativeteam/recruiter-job-tracker
- You should see 49 files committed
- Check that all folders appear: `config/`, `execution/`, `directives/`, etc.

---

## Next: Deploy to Railway

Once pushed to GitHub:

1. Go to https://railway.app/dashboard
2. Click "New Project" → "GitHub Repo"
3. Search for and select `recruiter-job-tracker`
4. Click "Deploy Now"
5. Railway will auto-deploy when it sees the Procfile

### Add Environment Variables
1. In Railway dashboard, go to Variables
2. Add these 6 variables:
   - `OPENAI_API_KEY`: Your OpenAI key
   - `APIFY_API_KEY`: Your Apify key
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase service role key
   - `WEBHOOK_URL`: Your webhook endpoint (e.g., https://webhook.site/your-id)
   - `PORT`: `5000`

3. Click "Deploy" to redeploy with environment variables

### Test the Deployment
```bash
# Get Railway URL from dashboard (something like https://recruiter-job-tracker-prod.railway.app)

# Test health endpoint
curl https://recruiter-job-tracker-prod.railway.app/health

# Expected response:
# {"status": "healthy", "timestamp": "2025-11-30T15:50:00Z"}
```

---

## Troubleshooting

### "Permission denied" error
- If using HTTPS: You didn't paste the token correctly, or token doesn't have `repo` scope
- If using SSH: Your public key wasn't added to GitHub, or you don't have permission to the repository

### Repository access issue
- Make sure you have access to `talkativeteam/recruiter-job-tracker`
- Check GitHub permissions at https://github.com/settings/organizations

### Git config issue
Set your git identity first:
```bash
git config --global user.email "your.email@example.com"
git config --global user.name "Your Name"
```

Then retry the push.
