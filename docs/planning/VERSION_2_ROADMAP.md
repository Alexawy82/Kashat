# LedgerLoop Version 2.0 - Production Readiness Roadmap

**Created**: December 15, 2025
**Updated**: December 16, 2025
**Current Status**: 95% (Production Ready)
**Target Status**: 97% (Production Ready)

---

## Overview

| Phase | Focus | Prompts | Est. Time |
|-------|-------|---------|-----------|
| 1 | Security (CRITICAL) | P1.1 - P1.5 | 2-3 days |
| 2 | Data Quality | P2.1 - P2.6 | 1 day |
| 3 | Error Handling & Stability | P3.1 - P3.4 | 1-2 days |
| 4 | Monitoring & Observability | P4.1 - P4.2 | 1 day |
| 5 | Feature Completion | P5.1 - P5.2 | 2-3 days |
| 6 | Polish & Deployment | P6.1 - P6.4 | 1-2 days |

---

## Progress Tracker

| Phase | Prompt | Description | Status |
|-------|--------|-------------|--------|
| **1** | P1.1 | JWT Authentication Backend | ✅ DONE |
| **1** | P1.2 | Protect All API Routes | ✅ DONE |
| **1** | P1.3 | Login UI Frontend | ✅ DONE |
| **1** | P1.4 | Rate Limiting | ✅ DONE |
| **1** | P1.5 | CORS Lockdown | ✅ DONE |
| **2** | P2.1 | Create Comprehensive Rules | ✅ DONE |
| **2** | P2.2 | Apply All Rules | ✅ DONE |
| **2** | P2.3 | Bulk AI Categorization | ✅ DONE |
| **2** | P2.4 | Transfer Detection | ✅ DONE |
| **2** | P2.5 | Recurring Detection | ✅ DONE |
| **2** | P2.6 | Data Quality Check | ✅ DONE |
| **3** | P3.1 | Standardize API Errors | ✅ DONE |
| **3** | P3.2 | Proper Logging | ✅ DONE |
| **3** | P3.3 | Frontend Error Boundaries | ✅ DONE |
| **3** | P3.4 | Fix Route Inconsistencies | ✅ DONE |
| **4** | P4.1 | Enhanced Prometheus Metrics | ✅ DONE |
| **4** | P4.2 | Enhanced Health Check | ✅ DONE |
| **5** | P5.1 | Predictive Analytics | ✅ DONE |
| **5** | P5.2 | Real-time WebSocket | ✅ DONE |
| **6** | P6.1 | UX Polish | ✅ DONE |
| **6** | P6.2 | Production Docker | ✅ DONE |
| **6** | P6.3 | User Documentation | ✅ DONE |
| **6** | P6.4 | Final Verification | ✅ DONE |

---

# 🔐 PHASE 1: SECURITY (Critical)

## Prompt P1.1: Add JWT Authentication Backend ✅ DONE

```
In C:\Users\Marwan\Desktop\AI\Flos

Implement JWT authentication for the backend:

NOTE: Authentication is currently disabled for single-user deployments; this section is optional future work.

1. Install required packages:
   pip install python-jose[cryptography] passlib[bcrypt]
   
   Add to requirements.txt:
   - python-jose[cryptography]
   - passlib[bcrypt]

2. Create apps/backend/src/ledgerloop/auth.py with:
   - JWT token creation/validation functions
   - Password hashing with bcrypt
   - Token expiry (24 hours for access, 7 days for refresh)
   - Secret key from environment variable LEDGERLOOP_JWT_SECRET

3. Create a simple user model (we'll use single-user for now):
   - Store in settings table or new user table
   - Fields: username, hashed_password, created_at
   - Default user: admin / admin (force change on first login)

4. Create apps/backend/src/ledgerloop/api/routes/auth.py with endpoints:
   - POST /api/auth/login - Returns access_token and refresh_token
   - POST /api/auth/refresh - Refresh access token
   - POST /api/auth/logout - Invalidate token (optional blacklist)
   - GET /api/auth/me - Get current user info
   - POST /api/auth/change-password - Change password

5. Create a dependency function get_current_user() that:
   - Extracts JWT from Authorization: Bearer header
   - Validates token
   - Returns user or raises 401

6. Register the auth router in main.py

7. Test the endpoints:
   curl -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin"}'
```

---

## Prompt P1.2: Protect All API Routes ✅ DONE

```
In C:\Users\Marwan\Desktop\AI\Flos

Add authentication requirement to all API routes:

1. In apps/backend/src/ledgerloop/api/main.py:
   - Import the get_current_user dependency
   - Create a list of PUBLIC_ROUTES that don't need auth:
     - /api/health
     - /api/auth/login
     - /api/auth/refresh
   - Add middleware or dependency that checks auth for all other routes

2. For each route file in apps/backend/src/ledgerloop/api/routes/:
   - Add Depends(get_current_user) to routes that need protection
   - Or use a global approach with middleware

3. The recommended approach - create a protected router:
   ```python
   from fastapi import APIRouter, Depends
   from ledgerloop.auth import get_current_user
   
   protected_router = APIRouter(dependencies=[Depends(get_current_user)])
   ```
   
   Then mount all sensitive routes on protected_router

4. Test that protected routes return 401 without token:
   curl http://localhost:8000/api/transactions
   # Should return 401 Unauthorized

5. Test that protected routes work WITH token:
   TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin"}' | jq -r '.access_token')
   
   curl http://localhost:8000/api/transactions \
     -H "Authorization: Bearer $TOKEN"
   # Should return transactions

6. Verify these remain public:
   curl http://localhost:8000/api/health
   # Should work without token
```

---

## Prompt P1.3: Add Login UI to Frontend

```
In C:\Users\Marwan\Desktop\AI\Flos\apps\web

Create login UI and auth state management:

1. Create src/contexts/AuthContext.tsx:
   - AuthProvider component
   - State: user, token, isAuthenticated, isLoading
   - Functions: login, logout, refreshToken
   - Store token in localStorage
   - Auto-refresh token before expiry

2. Create src/app/login/page.tsx:
   - Simple login form (username, password)
   - Error handling for invalid credentials
   - Redirect to dashboard on success
   - "Remember me" checkbox (optional)

3. Create src/components/auth/ProtectedRoute.tsx:
   - HOC or wrapper component
   - Redirects to /login if not authenticated
   - Shows loading while checking auth

4. Update src/app/layout.tsx:
   - Wrap app in AuthProvider
   - Add auth check logic

5. Update src/utils/api.ts (or create if doesn't exist):
   - Add token to all API requests automatically
   - Handle 401 responses (redirect to login)
   - Add refresh token logic on 401

6. Protect all pages except /login:
   - Wrap page components in ProtectedRoute
   - Or use middleware.ts for route protection

7. Add logout button to navigation/header

8. Test the flow:
   - Visit /transactions without login → redirected to /login
   - Login with admin/admin → redirected to dashboard
   - Refresh page → stays logged in (token in localStorage)
   - Click logout → redirected to login
```

---

## Prompt P1.4: Add Rate Limiting

```
In C:\Users\Marwan\Desktop\AI\Flos

Add rate limiting to protect the API:

1. Install slowapi:
   pip install slowapi
   
   Add to requirements.txt

2. Update apps/backend/src/ledgerloop/api/main.py:
   ```python
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   from slowapi.errors import RateLimitExceeded
   
   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```

3. Add rate limits to sensitive endpoints:
   - POST /api/auth/login: 5/minute (prevent brute force)
   - POST /api/import/*: 10/minute (heavy operations)
   - GET /api/transactions: 60/minute (normal usage)
   - POST /api/ai/*: 20/minute (AI operations)
   - Default for others: 100/minute

4. Example usage on a route:
   ```python
   @router.post("/login")
   @limiter.limit("5/minute")
   async def login(request: Request, ...):
   ```

5. Test rate limiting:
   # Should work first 5 times
   for i in {1..6}; do
     curl -X POST http://localhost:8000/api/auth/login \
       -H "Content-Type: application/json" \
       -d '{"username": "wrong", "password": "wrong"}'
     echo ""
   done
   # 6th request should return 429 Too Many Requests
```

---

## Prompt P1.5: Lock Down CORS

```
In C:\Users\Marwan\Desktop\AI\Flos

Configure CORS properly for production:

1. Update apps/backend/src/ledgerloop/api/main.py:
   
   Current (permissive):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # TOO PERMISSIVE
       ...
   )
   ```
   
   Change to:
   ```python
   import os
   
   ALLOWED_ORIGINS = os.getenv("LEDGERLOOP_CORS_ORIGINS", "http://localhost:3000").split(",")
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=ALLOWED_ORIGINS,
       allow_credentials=True,
       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```

2. Update .env.example with:
   ```
   # CORS - comma separated origins
   LEDGERLOOP_CORS_ORIGINS=http://localhost:3000
   # For production: LEDGERLOOP_CORS_ORIGINS=https://yourdomain.com
   ```

3. Test CORS is working:
   - Frontend at localhost:3000 can still make requests
   - Requests from other origins are blocked

4. Document in README the CORS configuration for production
```

---

# 📊 PHASE 2: DATA QUALITY

## Prompt P2.1: Create Comprehensive Rules

```
In C:\Users\Marwan\Desktop\AI\Flos

Create rules to categorize more transactions:

1. First, analyze uncategorized transactions to find patterns:
   curl "http://localhost:8000/api/transactions?has_category=false&limit=200" \
     -H "Authorization: Bearer $TOKEN" > uncategorized.json
   
   Look for common merchants/patterns in the descriptions

2. Get category IDs:
   curl http://localhost:8000/api/categories -H "Authorization: Bearer $TOKEN"

3. Create rules for common merchants (adjust category IDs as needed):

   # Restaurants & Fast Food
   - Pattern: "chick-fil-a|mcdonald|wendy|burger|taco bell|chipotle|panera|subway|pizza|domino|papa john"
   - Category: Food & Dining

   # Coffee
   - Pattern: "starbucks|dunkin|coffee"
   - Category: Food & Dining

   # Grocery Stores
   - Pattern: "walmart|target|kroger|publix|aldi|lidl|whole foods|trader joe|harris teeter|food lion|grocery"
   - Category: Grocery

   # Gas Stations
   - Pattern: "sheetz|wawa|speedway|circle k|racetrac|marathon|sunoco|valero|citgo|murphy"
   - Category: Gas & Automotive

   # Utilities
   - Pattern: "duke energy|power|electric|water|gas bill|utility|verizon|att|t-mobile|spectrum|comcast|xfinity"
   - Category: Bills & Utilities

   # Subscriptions
   - Pattern: "netflix|spotify|hulu|disney|hbo|apple\\.com|youtube|amazon prime|audible|dropbox|google storage|icloud"
   - Category: Subscriptions

   # Online Shopping
   - Pattern: "amazon|ebay|etsy|wayfair|best buy|home depot|lowes|ikea"
   - Category: Shopping

   # PayPal
   - Pattern: "paypal"
   - Category: Shopping (lower priority)

   # Income
   - Pattern: "payroll|direct dep|salary|wage|ach.*employer|employer"
   - Category: Income, set is_income=true

   # Bank fees
   - Pattern: "service charge|monthly fee|overdraft|nsf fee|atm fee"
   - Category: Banking

4. List all rules after creation
```

---

## Prompt P2.2: Apply All Rules

```
In C:\Users\Marwan\Desktop\AI\Flos

Apply all rules to categorize transactions:

1. Get list of all rules:
   curl http://localhost:8000/api/rules -H "Authorization: Bearer $TOKEN"

2. For each rule, apply it:
   RULES=$(curl -s http://localhost:8000/api/rules -H "Authorization: Bearer $TOKEN" | jq -r '.[].id')
   
   for RULE_ID in $RULES; do
     echo "Applying rule: $RULE_ID"
     curl -X POST "http://localhost:8000/api/rules/$RULE_ID/apply" \
       -H "Authorization: Bearer $TOKEN"
   done

3. Check categorization improvement:
   - Count categorized before and after
   - Calculate new percentage
```

---

## Prompt P2.3: Run Bulk AI Categorization

```
In C:\Users\Marwan\Desktop\AI\Flos

Run AI categorization on remaining uncategorized transactions:

1. Check current uncategorized count

2. Run bulk AI enhancement:
   curl -X POST "http://localhost:8000/api/ai/enhance/uncategorized" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"limit": 500, "min_confidence": 0.6}'

3. Monitor job progress if async

4. Run multiple batches if needed

5. Check final categorization stats
```

---

## Prompt P2.4: Run Transfer Detection

```
In C:\Users\Marwan\Desktop\AI\Flos

Run transfer detection to find internal transfers:

1. Check current transfer state
2. Run V2 transfer detection
3. If V2 finds nothing (single account), try V1
4. Review and confirm valid transfers
5. Report results
```

---

## Prompt P2.5: Run Recurring Detection

```
In C:\Users\Marwan\Desktop\AI\Flos

Run recurring/subscription detection:

1. Check current recurring state
2. Run recurring detection
3. Review detected series
4. Confirm valid recurring series
5. Report total monthly recurring spend
```

---

## Prompt P2.6: Data Quality Check

```
In C:\Users\Marwan\Desktop\AI\Flos

Generate a data quality report after Phase 2:

1. Get comprehensive stats:
   - Total transactions
   - Categorized count and percentage
   - Rules count
   - Transfers detected
   - Recurring series

2. Create before/after comparison table

3. List remaining uncategorized patterns
```

---

# 🛠️ PHASE 3: ERROR HANDLING & STABILITY

## Prompt P3.1: Standardize API Error Responses

```
In C:\Users\Marwan\Desktop\AI\Flos

Create consistent error response format across all API endpoints:

1. Create apps/backend/src/ledgerloop/api/errors.py with:
   - ErrorResponse model
   - AppException base class
   - NotFoundError, ValidationError, AuthenticationError, AuthorizationError
   - Exception handlers

2. Register exception handlers in main.py

3. Update route files to use new exceptions

4. Test error responses are consistent
```

---

## Prompt P3.2: Add Proper Logging

```
In C:\Users\Marwan\Desktop\AI\Flos

Replace print statements with proper structured logging:

1. Create logging_config.py with JSON formatter

2. Initialize logging in main.py

3. Search and replace print statements with logging calls

4. Add request logging middleware

5. Test logging output
```

---

## Prompt P3.3: Add Frontend Error Boundaries

```
In C:\Users\Marwan\Desktop\AI\Flos\apps\web

Add error boundaries to catch and display errors gracefully:

1. Create ErrorBoundary component
2. Create ApiErrorDisplay component
3. Wrap layout with ErrorBoundary
4. Update API utility for consistent error handling
5. Test error handling
```

---

## Prompt P3.4: Fix API Route Inconsistencies

```
In C:\Users\Marwan\Desktop\AI\Flos

Fix naming inconsistencies in API routes:

1. Identify inconsistencies (/imports vs /import, etc.)
2. Standardize to consistent naming convention
3. Update backend and frontend to match
4. Test all endpoints still work
```

---

# 📈 PHASE 4: MONITORING & OBSERVABILITY

## Prompt P4.1: Enhanced Prometheus Metrics

```
In C:\Users\Marwan\Desktop\AI\Flos

Enhance the metrics endpoint with more useful data:

1. Add counters: http_requests_total, transactions_imported, ai_categorizations
2. Add histograms: request_duration, ai_response_time
3. Add gauges: total_transactions, categorized_transactions, uncategorized_transactions
4. Add middleware to track request metrics
5. Test metrics endpoint
```

---

## Prompt P4.2: Enhanced Health Check

```
In C:\Users\Marwan\Desktop\AI\Flos

Enhance health check to provide more detailed status:

1. Basic /health endpoint
2. Detailed /health/detailed with component checks
3. Kubernetes-style /health/ready and /health/live
4. Test all health endpoints
```

---

# ✨ PHASE 5: FEATURE COMPLETION

## Prompt P5.1: Integrate Predictive Analytics

```
In C:\Users\Marwan\Desktop\AI\Flos

Integrate the existing ai_forecasting.py module with the UI:

1. Check what ai_forecasting.py provides
2. Create/update API endpoints for predictions
3. If module needs implementation, create basic predictive logic
4. Test endpoints
5. Update frontend to display predictions
```

---

## Prompt P5.2: Connect Real-time WebSocket

```
In C:\Users\Marwan\Desktop\AI\Flos

Connect the WebSocket infrastructure to actual events:

1. Check existing WebSocket setup
2. Ensure WebSocket endpoint exists
3. Emit events when data changes
4. Update frontend WebSocket hook
5. Test real-time updates
```

---

# 🎨 PHASE 6: POLISH & DEPLOYMENT

## Prompt P6.1: UX Polish

```
In C:\Users\Marwan\Desktop\AI\Flos\apps\web

Polish the user experience:

1. Add loading states to all pages
2. Add empty states
3. Add success/error toasts
4. Improve navigation
5. Add confirmation dialogs
6. Improve mobile responsiveness
```

---

## Prompt P6.2: Production Docker Configuration

```
In C:\Users\Marwan\Desktop\AI\Flos

Update Docker configuration for production:

1. Update Dockerfile.backend for production
2. Update Dockerfile.web for production
3. Update docker-compose.yml for production
4. Create production .env.example
5. Test Docker build
```

---

## Prompt P6.3: Create User Documentation

```
In C:\Users\Marwan\Desktop\AI\Flos

Create basic user documentation:

1. Create docs/USER_GUIDE.md
2. Create docs/DEPLOYMENT.md
3. Create docs/TROUBLESHOOTING.md
4. Update README.md
```

---

## Prompt P6.4: Final Verification

```
In C:\Users\Marwan\Desktop\AI\Flos

Run final verification to confirm everything works:

1. Run all backend tests
2. Build frontend
3. Test authentication flow
4. Test all major features
5. Check health endpoints
6. Generate final stats
7. Update READINESS_ASSESSMENT.md with new scores
```

---

# Target Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Overall Completion | 73% | 97% |
| Backend | 85% | 95% |
| Frontend | 80% | 95% |
| Features | 72% | 90% |
| Production Readiness | 55% | 95% |
| Security | 37% | 90% |
| Categorization | 31% | 70%+ |

---

*Document Version: 2.0*
*Last Updated: December 15, 2025*
