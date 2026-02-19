# POS AI - Mobile Application

React Native mobile app for POS AI system.

## Features

### ✅ Authentication
- Login with email/password
- JWT token storage
- Auto-login on app restart

### ✅ Point of Sale (POS Screen)
- Product grid with search
- Shopping cart with quantity controls
- Real-time total calculation
- Checkout flow
- Vietnamese currency formatting

### ✅ Product Management
- List all products with search
- Create new products
- Edit existing products
- Delete products
- Category selection
- Form validation

## Tech Stack

- **React Native** - Cross-platform mobile framework
- **TypeScript** - Type safety
- **AsyncStorage** - Local data persistence
- **Fetch API** - HTTP client for backend communication

## Installation

```bash
# Install dependencies
npm install
# or
yarn install

# iOS
cd ios && pod install && cd ..
npx react-native run-ios

# Android
npx react-native run-android
```

## Configuration

Update `API_BASE_URL` in `src/services/api.ts`:

```typescript
const API_BASE_URL = 'http://YOUR_BACKEND_URL/api/v1';
```

For local development:
- iOS Simulator: `http://localhost:8000/api/v1`
- Android Emulator: `http://10.0.2.2:8000/api/v1`
- Physical Device: `http://YOUR_LOCAL_IP:8000/api/v1`

## Project Structure

```
mobile/
├── src/
│   ├── screens/
│   │   ├── LoginScreen.tsx      # Authentication
│   │   ├── POSScreen.tsx        # Main POS interface
│   │   └── ProductsScreen.tsx   # Product management
│   ├── services/
│   │   └── api.ts               # API client
│   ├── components/              # Reusable components
│   ├── hooks/                   # Custom React hooks
│   ├── types/                   # TypeScript types
│   ├── utils/                   # Utility functions
│   └── App.tsx                  # Main app component
├── package.json
└── README.md
```

## Screens

### Login Screen
- Email & password input
- Error handling
- Loading state

### POS Screen (Main)
- Left panel: Product grid with search
- Right panel: Shopping cart
- Add products to cart by tapping
- Adjust quantities with +/- buttons
- Display total price
- Checkout button

### Products Screen
- List all products
- Search functionality
- Add new product button
- Edit/Delete actions for each product
- Modal form for create/edit
- Input validation

## API Integration

All API calls go through `src/services/api.ts`:

- `login(email, password)` - Authenticate user
- `getProducts(params)` - List products with pagination/search
- `getProduct(id)` - Get single product
- `createProduct(data)` - Create new product
- `updateProduct(id, data)` - Update product
- `deleteProduct(id)` - Delete product
- `getCategories()` - List categories

## Future Enhancements

- [ ] React Navigation for better routing
- [ ] Offline mode with local SQLite
- [ ] Barcode scanning
- [ ] Receipt printing
- [ ] Order history
- [ ] Analytics dashboard
- [ ] Multi-store support
- [ ] Real-time sync
- [ ] Push notifications

## Testing

```bash
npm test
# or
yarn test
```

## Build for Production

```bash
# iOS
npx react-native run-ios --configuration Release

# Android
cd android
./gradlew assembleRelease
# APK: android/app/build/outputs/apk/release/app-release.apk
```

## License

Private - TPPlaza
