# Workflow Verification Frontend

Next.js frontend for the Workflow Verification System.

## Features

1. **File Upload** - Upload workflow.json and transcript.json files
2. **Audit Dashboard** - View overall compliance scores and metrics
3. **Graph Visualizer** - Interactive workflow graph with colored nodes based on status
4. **Transcript Viewer** - Conversation turns with evidence highlighting
5. **History Table** - View past verification runs

## Tech Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **shadcn/ui** - Pre-built UI components
- **ReactFlow** - Graph visualization
- **Lucide React** - Icons

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   # .env.local file already created
   FASTAPI_URL=http://localhost:8000
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:3000 (or 3001 if 3000 is in use)

## Usage

1. **Start the FastAPI backend first:**
   ```bash
   cd ..
   source .venv/bin/activate
   uvicorn src.main:app --reload
   ```

2. **Access the frontend:**
   Open http://localhost:3001 in your browser

3. **Upload files:**
   - Click "Choose workflow file..." and select a workflow JSON
   - Click "Choose transcript file..." and select a transcript JSON
   - Click "Run Verification"

4. **View results:**
   - **Dashboard tab**: Overall scores and metrics
   - **Graph tab**: Interactive workflow visualization
   - **Transcript tab**: Conversation with evidence
   - **History tab**: Past verification runs

## Architecture

### Next.js API Routes (Proxy)

Frontend communicates ONLY with Next.js API routes, which proxy to FastAPI:

- `POST /api/verify` → `POST http://localhost:8000/api/verify`
- `GET /api/verify/{id}` → `GET http://localhost:8000/api/verify/{id}`
- `GET /api/verify/recent` → `GET http://localhost:8000/api/verify/recent`

### Components

- `FileUpload.tsx` - File upload and verification trigger
- `AuditDashboard.tsx` - Metrics and scores display
- `GraphVisualizer.tsx` - ReactFlow graph with colored nodes
- `TranscriptViewer.tsx` - Conversation turns with evidence
- `HistoryTable.tsx` - List of past verifications

### Color Coding

- **Green** (✓) - Visited nodes
- **Yellow** (⚠) - Partial match
- **Red** (✗) - Skipped nodes
- **Orange** (❗) - Incorrect nodes
- **Purple** (🔄) - Repeated nodes

## Development

### Build for production:
```bash
npm run build
npm start
```

### Type checking:
```bash
npx tsc --noEmit
```

### Linting:
```bash
npm run lint
```

## Troubleshooting

### Port already in use
Next.js will automatically use port 3001 if 3000 is taken. Check the console output for the actual port.

### API connection errors
1. Verify FastAPI backend is running on http://localhost:8000
2. Check `.env.local` has correct `FASTAPI_URL`
3. Check FastAPI CORS settings allow http://localhost:3001

### Module not found
```bash
rm -rf node_modules .next
npm install
```

## File Structure

```
frontend/
├── app/
│   ├── api/                    # Next.js API routes (proxy to FastAPI)
│   │   └── verify/
│   │       ├── route.ts        # POST /api/verify
│   │       ├── [id]/route.ts   # GET /api/verify/{id}
│   │       └── recent/route.ts # GET /api/verify/recent
│   ├── page.tsx                # Main page
│   ├── layout.tsx              # Root layout
│   └── globals.css             # Global styles
├── components/
│   ├── ui/                     # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── tabs.tsx
│   ├── FileUpload.tsx          # Component 1: Upload
│   ├── AuditDashboard.tsx      # Component 2: Dashboard
│   ├── GraphVisualizer.tsx     # Component 3: Graph
│   ├── TranscriptViewer.tsx    # Component 4: Transcript
│   └── HistoryTable.tsx        # Component 5: History
├── lib/
│   ├── types.ts                # TypeScript types
│   └── utils.ts                # Utility functions
└── .env.local                  # Environment variables
```

## Notes

- Frontend uses Next.js API routes as a proxy layer for security
- All FastAPI communication goes through Next.js backend
- Graph visualization requires ReactFlow library
- File uploads are processed client-side (no multipart upload to backend)
