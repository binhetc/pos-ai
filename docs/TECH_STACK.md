# Tech Stack Decision - POS AI

## Quyết định: 18/02/2026

### Mobile App: React Native + TypeScript
- **Lý do:** Cross-platform (tablet Android là chính, hỗ trợ iOS), ecosystem lớn, TypeScript cho type-safety
- **Alternatives xét:** Flutter (ít lib hardware), Native (cost x2)
- **Risk:** Performance với camera AI → mitigate bằng native module

### Backend: Python 3.11 / FastAPI
- **Lý do:** Async native, auto-generate API docs, ecosystem AI/ML mạnh nhất (TensorFlow, OpenCV, LangChain)
- **Alternatives xét:** Node.js (yếu ML), Go (ít lib AI), Java Spring (overkill)
- **Risk:** GIL cho CPU-bound AI tasks → mitigate bằng worker process / Celery

### Database: PostgreSQL 16
- **Lý do:** ACID cho transactions tài chính, JSONB cho flexible product attributes, full-text search cho tìm sản phẩm
- **Alternatives xét:** MySQL (kém JSON support), MongoDB (không ACID native)

### Cache: Redis 7
- **Lý do:** Session management, inventory locking (prevent oversell), message queue cho async tasks

### Auth: JWT + RBAC
- 3 roles: **Owner** (full access) → **Manager** (store-level) → **Cashier** (POS only)
- Token expire: 8h (1 ca làm việc)
- Refresh token: 30 days

### CI/CD: GitHub Actions
- Pipeline: Lint → Unit Test → Integration Test → Build → Deploy staging
- Branch strategy: main (prod) ← develop ← feature/*

### Deployment: AWS
- ECS Fargate (backend containers)
- RDS PostgreSQL (managed DB)
- ElastiCache Redis
- S3 + CloudFront (mobile assets, product images)
- Cost estimate: ~$150-200/month cho MVP
