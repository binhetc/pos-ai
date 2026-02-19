# POS AI - Hệ thống bán hàng thông minh tích hợp AI

> Dự án POS cho TPPlaza - tích hợp AI để nâng cao trải nghiệm bán hàng

## Tech Stack

| Layer | Technology | Lý do chọn |
|-------|-----------|-------------|
| **POS App** | React Native + TypeScript | Cross-platform (iOS/Android/tablet), type-safe, ecosystem lớn |
| **Backend** | Python 3.11+ / FastAPI | Async, auto-docs (Swagger), dễ tích hợp AI/ML |
| **ORM** | SQLAlchemy 2.0 | Mature, async support, migration via Alembic |
| **Database** | PostgreSQL 16 | ACID, JSON support, full-text search, proven at scale |
| **Cache** | Redis 7 | Session, queue, real-time inventory lock |
| **AI/ML** | TensorFlow, OpenCV, LangChain | Computer vision (product recognition), NLP (voice command) |
| **Auth** | JWT + Role-based (RBAC) | Stateless, 3 roles: owner/manager/cashier |
| **CI/CD** | GitHub Actions | Lint → Test → Build → Deploy |
| **Cloud** | AWS (ECS/RDS/ElastiCache) | Reliable, cost-effective cho startup |
| **Hardware** | Barcode scanner, receipt printer, payment terminal | USB/Bluetooth integration via React Native |

## Project Structure

```
pos-ai/
├── mobile/          # React Native POS app
├── backend/         # FastAPI backend
│   ├── app/
│   │   ├── api/     # Route handlers
│   │   ├── models/  # SQLAlchemy models
│   │   ├── schemas/ # Pydantic schemas
│   │   ├── services/# Business logic
│   │   ├── ai/      # AI/ML modules
│   │   └── core/    # Config, security, deps
│   ├── alembic/     # DB migrations
│   └── tests/
├── docs/            # Technical documentation
├── .github/workflows/  # CI/CD
└── docker-compose.yml
```

## Tính năng AI (Sprint 2+)

1. 📷 Nhận diện sản phẩm bằng camera (Computer Vision)
2. 💡 Gợi ý sản phẩm cho khách (Recommendation Engine)
3. 📊 Dự báo tồn kho (Demand Forecasting)
4. 👤 Phân tích hành vi khách hàng
5. 🎤 Voice command cho nhân viên

## Getting Started

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Mobile
cd mobile
npm install
npx react-native start
```

## Sprint 1 (Hoàn thành: 19/02/2026) ✅

- [x] Setup repo + CI/CD (#1)
- [x] Tech stack documentation
- [x] Database schema design (#2)
- [x] Authentication system (RBAC) (#3)
- [x] POS UI prototype (#10)
- [x] Product catalog CRUD (#9)
- [x] Code review fixes (#8)
- [x] Order Management API

## Sprint 2 (Deadline: 15/04/2026)

### Core Features
- [ ] Customer Management API & UI
- [ ] Reporting & Analytics (daily sales, inventory turnover)
- [ ] Receipt printing integration
- [ ] Barcode scanner integration (USB/Bluetooth)
- [ ] Payment terminal integration
- [ ] Multi-store support

### AI Features (Phase 1)
- [ ] Product recognition via camera (Computer Vision)
  - OpenCV + TensorFlow Lite model
  - Real-time barcode scanning fallback
- [ ] Basic recommendation engine
  - Frequently bought together
  - Category-based suggestions

### DevOps
- [ ] Docker deployment setup
- [ ] AWS infrastructure (ECS + RDS + ElastiCache)
- [ ] Production monitoring & logging
