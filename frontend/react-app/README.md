# React + TypeScript Frontend (Vite + Tailwind)

## Setup
```bash
cd frontend/react-app
npm install
# or pnpm/yarn if you prefer
```

Create a `.env` (or `.env.local`) to point to the FastAPI backend:
```
VITE_API_BASE_URL=http://localhost:8000
```

## Run
```bash
npm run dev
# open http://localhost:5173
```

## Build
```bash
npm run build
npm run preview
```

## Features
- Upload DICOM/PNG/JPG
- Toggle inclusion of retrieved images in GPT prompt
- Shows generated description, quality badge, retrieved references
- Regenerate button for low-quality results
- History list with quick restore

## Notes
- Tailwind configured via `tailwind.config.js`
- API client uses `VITE_API_BASE_URL` (defaults to `http://localhost:8000` if unset)
- Uses axios for API calls, keeps responses strongly typed






