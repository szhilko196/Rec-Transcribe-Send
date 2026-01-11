# RAGFlow Login Instructions - READY TO USE ✅

## Status: User Account Created Successfully

A regular user account has been created in the database with proper password hashing.

## Login Credentials

**Access the web UI**: http://localhost:9380

**Login with**:
- **Email**: `user@ragflow.io`
- **Password**: `admin`

## What Was Done

1. **Admin User Created** (for Admin UI only):
   - Email: `admin@ragflow.io`
   - Password: `admin`
   - Note: This account can only be used for Admin UI at http://localhost:9380/admin

2. **Regular User Created** (for normal login):
   - Email: `user@ragflow.io`
   - Password: `admin`
   - Password hash: `scrypt:32768:8:1$...` (properly hashed using werkzeug)

## How to Login

### Option 1: Web UI (Recommended)

1. **Open your browser** and go to: http://localhost:9380
2. **Enter credentials**:
   - Email: `user@ragflow.io`
   - Password: `admin`
3. **Click Login**

The web UI handles password encryption automatically before sending to the API.

### Option 2: Create Additional Users

Use the Admin UI to create more users:

1. Go to: http://localhost:9380/admin
2. Login with: `admin@ragflow.io` / `admin`
3. Click "New User" button
4. Fill in user details and create account

## Next Steps - Generate API Key

Once logged in:

1. **Navigate to Settings** → **API Keys**
2. **Click "Create New Key"**
3. **Copy the generated key**
4. **Add to root .env file**:
   ```env
   RAGFLOW_API_KEY=your-generated-key-here
   ```
5. **Enable RAG indexing**:
   ```env
   ENABLE_RAG_INDEXING=true
   ```

## Technical Notes

### Password Encryption Flow

The RAGFlow authentication uses multi-layer security:

1. **Client-side**: Password is base64 encoded and encrypted using a cipher
2. **Server-side**: Encrypted password is decrypted, then verified against scrypt hash
3. **Storage**: Password stored as scrypt hash in database

**Why API login fails**:
- The `/v1/user/login` endpoint expects encrypted password (from web UI)
- Direct API calls with plain/base64 password return "Fail to crypt password"
- **Solution**: Use the web UI which handles encryption automatically

### Database Details

**User table entry**:
```
id: 92d97283eee911f0a61d5e468e32d24d
email: user@ragflow.io
nickname: User
password: scrypt:32768:8:1$NryHC8tJy6SZx... (truncated)
is_superuser: 0
status: 1 (active)
```

### Admin vs Regular User

| Feature | Admin User | Regular User |
|---------|-----------|--------------|
| Email | admin@ragflow.io | user@ragflow.io |
| Web UI Login | ❌ No | ✅ Yes |
| Admin UI Login | ✅ Yes | ❌ No |
| Admin CLI | ✅ Yes | ❌ No |
| API Key Generation | ❌ No | ✅ Yes |
| Create Datasets | ❌ No | ✅ Yes |

## Troubleshooting

### "Fail to crypt password" error
- **Cause**: Trying to login via API without client-side encryption
- **Solution**: Use the web UI at http://localhost:9380

### Can't access http://localhost:9380
- **Check services**: `docker-compose -f services/RAG-search/docker-compose.ragflow.yml ps`
- **Restart if needed**: `docker-compose -f services/RAG-search/docker-compose.ragflow.yml restart ragflow`

### Forgot password
- Use Admin CLI to reset: `docker exec ragflow bash -c "cd /ragflow && python3 api/utils/commands.py reset_password user@ragflow.io newpassword newpassword"`
- Or recreate user via database (as shown in setup process)

## Security Recommendations

1. **Change default password** after first login
2. **Use strong passwords** for production
3. **Rotate API keys** regularly
4. **Enable HTTPS** in production environments

---

**Status**: ✅ Ready to login at http://localhost:9380
**Created**: 2026-01-10
**User**: user@ragflow.io / admin
