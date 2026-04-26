# Setup Guide — MongoDB Atlas + Railway

---

## Part 1 — MongoDB Atlas (free cloud database)

### Step 1 — Create a free account
1. Go to https://www.mongodb.com/cloud/atlas/register
2. Sign up with Google or email — it's free, no card needed.

### Step 2 — Create a free cluster
1. After login, click **"Build a Database"**
2. Choose **M0 Free** (512MB, plenty for this app)
3. Pick any cloud provider and region closest to you (e.g. AWS Mumbai)
4. Name your cluster anything, e.g. `expenses-cluster`
5. Click **"Create"** — takes about 2 minutes to provision

### Step 3 — Create a database user
1. In the left sidebar go to **Security → Database Access**
2. Click **"Add New Database User"**
3. Choose **Password** authentication
4. Set:
   - Username: `etadmin`
   - Password: `Souvik3751` (or whatever you want)
5. Under "Database User Privileges" select **"Read and write to any database"**
6. Click **"Add User"**

### Step 4 — Allow network access from anywhere
> Railway's servers have dynamic IPs, so we must allow all IPs.

1. In the left sidebar go to **Security → Network Access**
2. Click **"Add IP Address"**
3. Click **"Allow Access from Anywhere"** → this adds `0.0.0.0/0`
4. Click **"Confirm"**

### Step 5 — Get your connection string
1. In the left sidebar go to **Deployment → Database**
2. Click **"Connect"** on your cluster
3. Choose **"Drivers"**
4. Select **Python** / version **3.6 or later**
5. Copy the connection string — it looks like this:

```
mongodb+srv://etadmin:<password>@expenses-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

6. Replace `<password>` with your actual password (`Souvik3751`):

```
mongodb+srv://etadmin:Souvik3751@expenses-cluster.xxxxx.mongodb.net/expenses_db?retryWrites=true&w=majority
```

> Note: `expenses_db` at the end is the database name — MongoDB creates it automatically on first use.

**Save this full URI — you will paste it into Railway in Part 2.**

---

## Part 2 — Deploy to Railway

### Step 1 — Prepare your project folder
Your folder should look exactly like this:

```
expenses-app/
├── app.py
├── Dockerfile
├── requirements.txt
├── railway.toml
├── .gitignore
└── static/
    └── index.html
```

### Step 2 — Push to GitHub
```bash
cd expenses-app
git init
git add .
git commit -m "initial commit"
# Create a new repo on github.com first, then:
git remote add origin https://github.com/YOUR_USERNAME/expenses-app.git
git push -u origin main
```

### Step 3 — Create a Railway project
1. Go to https://railway.app and log in (sign up free if needed)
2. Click **"New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Select your `expenses-app` repository
5. Railway detects the Dockerfile and starts building automatically

### Step 4 — Add environment variables
1. In Railway, click on your service (the card that appeared)
2. Go to the **"Variables"** tab
3. Add these two variables:

| Variable | Value |
|---|---|
| `MONGO_URI` | `mongodb+srv://etadmin:Souvik3751@expenses-cluster.xxxxx.mongodb.net/expenses_db?retryWrites=true&w=majority` |
| `SECRET_KEY` | Any random string, e.g. `x7k2mQ9pLnRvT4wY8cZ1aB3dE6fH0jN5` |

4. Click **"Deploy"** — Railway rebuilds with the new variables

### Step 5 — Get your public URL
1. Go to the **"Settings"** tab of your service
2. Under **"Networking"** click **"Generate Domain"**
3. Railway gives you a URL like `https://expenses-app-production.up.railway.app`
4. Open it in your browser — your app is live!

---

## Summary — what goes where

```
MongoDB Atlas (cloud DB, free)
  └── stores all users, income, expenses data
      ↑
      │  MONGO_URI (connection string)
      │
Railway (cloud server, free tier)
  └── runs your Flask app via Docker
      └── served at your-app.up.railway.app
```

No local Oracle, no tunneling, no port forwarding — everything is in the cloud.

---

## Troubleshooting

**Build fails on Railway**
- Check the build logs — usually a missing file in the repo
- Make sure `static/index.html` is committed to git (not in .gitignore)

**"Authentication failed" error**
- Double-check MONGO_URI in Railway variables
- Make sure the password in the URI matches what you set in Atlas Step 3
- No spaces around the `=` in Railway variables

**"Connection refused" / timeout**
- Go to Atlas → Network Access and confirm `0.0.0.0/0` is listed
- Wait 2-3 minutes after adding the IP rule for it to propagate

**App loads but data doesn't save**
- Check Railway logs (Deployments tab → click latest → View Logs)
- Look for Python tracebacks
