# 🚀 GitHub Workflow Guide - ROMS

Your private repo is live: **https://github.com/farzanariel/ROMS**

---

## ✅ What's Done

- ✅ Git repository initialized
- ✅ `.gitignore` created (protects secrets)
- ✅ All files committed
- ✅ Private GitHub repo created
- ✅ Code pushed to GitHub
- ✅ Update script created

---

## 📋 Quick Reference

### On Mac (Development)

**Make changes and push:**
```bash
cd /Users/farzan/Documents/Projects/ROMS

# After making changes...
git add .
git commit -m "Description of what you changed"
git push
```

**Check status:**
```bash
git status          # See what changed
git log --oneline   # See recent commits
```

---

### On Windows Server (Production)

**First time setup:**
```powershell
# Install Git (if not installed)
choco install git -y

# Clone the repo
cd C:\
git clone https://github.com/farzanariel/ROMS.git

# Navigate and setup
cd C:\ROMS\backend-v2
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

**Update from GitHub:**
```powershell
# Quick way (recommended)
cd C:\ROMS
.\update.ps1

# Manual way
cd C:\ROMS
git pull
nssm restart ROMS-V2-Backend
```

---

## 🔄 Daily Workflow

### 1. Develop on Mac

```bash
cd /Users/farzan/Documents/Projects/ROMS

# Edit your files...

# Stage all changes
git add .

# Commit with a message
git commit -m "Fixed webhook parser for new format"

# Push to GitHub
git push
```

### 2. Deploy to Windows Server

```powershell
# Open PowerShell as Administrator
cd C:\ROMS

# Pull and update everything
.\update.ps1
```

The `update.ps1` script will:
- ✅ Stop the service
- ✅ Pull latest code
- ✅ Update dependencies (if changed)
- ✅ Restart the service
- ✅ Run health check

---

## 📁 What's NOT in GitHub (Protected)

These files are in `.gitignore` and won't be pushed:

- ❌ `.env` (environment variables)
- ❌ `credentials.json` (Google API keys)
- ❌ `*.db` (database files)
- ❌ `venv/` (Python virtual environment)
- ❌ `node_modules/` (Node dependencies)
- ❌ `*.log` (log files)

**Important:** Manually copy these files to Windows Server!

---

## 🔐 Authenticating Windows Server with GitHub

**Option 1: HTTPS (Easiest)**
```powershell
# Windows will prompt for credentials on first git pull
# Use your GitHub username and a Personal Access Token (not password!)
```

**Generate Personal Access Token:**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (full control)
4. Copy the token
5. Use it as password when prompted

**Option 2: SSH (More Secure)**
```powershell
# Generate SSH key on Windows
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key
Get-Content C:\Users\Administrator\.ssh\id_ed25519.pub

# Add to GitHub:
# Settings → SSH and GPG keys → New SSH key

# Update remote URL
cd C:\ROMS
git remote set-url origin git@github.com:farzanariel/ROMS.git
```

---

## 🎯 Common Commands

### Mac

```bash
# Check what changed
git status

# See differences
git diff

# View commit history
git log --oneline -10

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Discard local changes
git checkout -- <file>

# Create a new branch
git checkout -b feature-name

# Switch branches
git checkout main
```

### Windows

```powershell
# Check status
git status

# Pull latest
git pull

# See what changed
git log --oneline -10

# Discard local changes
git checkout -- <file>
```

---

## 🚨 Troubleshooting

### "Conflicts" when pulling

```powershell
# On Windows, if you get merge conflicts:

# Option 1: Keep remote version (from Mac)
git fetch origin
git reset --hard origin/main

# Option 2: Stash local changes, pull, then reapply
git stash
git pull
git stash pop
```

### Can't push from Mac

```bash
# Make sure you're up to date
git pull

# Then push again
git push
```

### Authentication failed

```powershell
# Re-authenticate
gh auth login --web
```

---

## 📊 Example Full Workflow

**Scenario:** You fix a bug on Mac and deploy to Windows

**On Mac:**
```bash
cd /Users/farzan/Documents/Projects/ROMS

# Fix the bug in backend-v2/services/webhook_parser.py

# Stage changes
git add backend-v2/services/webhook_parser.py

# Commit
git commit -m "Fix: Handle empty order_number in webhook parser"

# Push
git push
```

**On Windows Server:**
```powershell
# Open PowerShell as Administrator
cd C:\ROMS

# Update everything
.\update.ps1

# Output shows:
# ✓ Service stopped
# ✓ Code updated
# ✓ Service started
# ✓ Health check passed
```

**Done! Bug fix deployed in < 1 minute! 🎉**

---

## 🎓 Learning Git

**Essential commands to know:**
- `git status` - See what's changed
- `git add .` - Stage all changes
- `git commit -m "message"` - Save changes locally
- `git push` - Upload to GitHub
- `git pull` - Download from GitHub
- `git log` - See history

**Resources:**
- GitHub Docs: https://docs.github.com/
- Git Cheat Sheet: https://education.github.com/git-cheat-sheet-education.pdf

---

## ✅ Quick Checklist

**On Mac:**
- [ ] Made your changes
- [ ] Tested locally
- [ ] `git add .`
- [ ] `git commit -m "description"`
- [ ] `git push`

**On Windows Server:**
- [ ] `cd C:\ROMS`
- [ ] `.\update.ps1`
- [ ] Verify site works

---

**Your GitHub repo:** https://github.com/farzanariel/ROMS

**Private** ✅ | **All code backed up** ✅ | **Easy sync** ✅

---

Need help? Just ask! 🚀

