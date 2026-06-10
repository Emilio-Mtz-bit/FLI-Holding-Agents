# File Upload UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Setup page's basic file count display with a reusable `FileDropZone` component that shows uploaded files as a removable list and supports incremental multi-upload.

**Architecture:** Extract a controlled `FileDropZone` component that owns the hidden `<input>` and renders file rows. Setup.tsx switches from DOM refs to `File[]` state arrays; FormData is built from those arrays at submit time.

**Tech Stack:** React 19, TypeScript, Tailwind v4, lucide-react (already installed)

---

## File Map

```
dashboard/src/
├── components/
│   └── FileDropZone.tsx    ← NEW: controlled dropzone + file list
└── pages/
    └── Setup.tsx           ← MODIFY: use FileDropZone, File[] state
```

---

## Task 1: FileDropZone component

**Files:**
- Create: `dashboard/src/components/FileDropZone.tsx`

- [ ] **Step 1: Create `dashboard/src/components/FileDropZone.tsx`**

```tsx
import { useRef } from 'react';
import { FileSpreadsheet, FileText, Image, File, X } from 'lucide-react';

interface FileDropZoneProps {
  label: string;
  accept: string;
  multiple: boolean;
  files: File[];
  onChange: (files: File[]) => void;
}

function formatSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split('.').pop()?.toLowerCase();
  if (ext === 'xlsx') return <FileSpreadsheet size={16} className="text-emerald-500 flex-shrink-0" />;
  if (ext === 'pdf') return <FileText size={16} className="text-rose-500 flex-shrink-0" />;
  if (['png', 'jpg', 'jpeg'].includes(ext ?? '')) return <Image size={16} className="text-blue-500 flex-shrink-0" />;
  return <File size={16} className="text-muted-foreground flex-shrink-0" />;
}

export default function FileDropZone({ label, accept, multiple, files, onChange }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handlePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    if (!picked.length) return;
    if (multiple) {
      const existing = new Set(files.map((f) => `${f.name}-${f.size}`));
      const fresh = picked.filter((f) => !existing.has(`${f.name}-${f.size}`));
      onChange([...files, ...fresh]);
    } else {
      onChange([picked[0]]);
    }
    e.target.value = '';
  };

  const remove = (idx: number) => onChange(files.filter((_, i) => i !== idx));

  return (
    <div className="space-y-2">
      <div
        className="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => inputRef.current?.click()}
      >
        <p className="text-sm text-muted-foreground">
          {files.length === 0
            ? `Click to select ${label}`
            : multiple
            ? '+ Add more files'
            : '↻ Replace file'}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={handlePick}
        />
      </div>

      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${f.size}`}
              className="flex items-center gap-2 px-3 py-2 rounded-md border bg-muted/30 text-sm"
            >
              <FileIcon name={f.name} />
              <span className="flex-1 truncate" title={f.name}>{f.name}</span>
              <span className="text-xs text-muted-foreground flex-shrink-0">{formatSize(f.size)}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); remove(i); }}
                className="text-muted-foreground hover:text-destructive transition-colors flex-shrink-0"
              >
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings/dashboard"
npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Commit**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings"
git add dashboard/src/components/FileDropZone.tsx
git commit -m "feat(dashboard): FileDropZone component with append list"
```

---

## Task 2: Wire FileDropZone into Setup page

**Files:**
- Modify: `dashboard/src/pages/Setup.tsx`

- [ ] **Step 1: Replace Setup.tsx**

Full replacement of `dashboard/src/pages/Setup.tsx`:

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAnalysisStore } from '@/store/analysis';
import { initScenarioCards } from '@/lib/scenarios';
import { compact } from '@/lib/format';
import ProgressBar from '@/components/ProgressBar';
import FileDropZone from '@/components/FileDropZone';
import { Upload } from 'lucide-react';

export default function Setup() {
  const navigate = useNavigate();

  const [period, setPeriod] = useState('ENERO 2026');
  const [year, setYear] = useState(2026);
  const [company, setCompany] = useState('Grupo Nama');
  const [xlsxFiles, setXlsxFiles] = useState<File[]>([]);
  const [qualFiles, setQualFiles] = useState<File[]>([]);

  const { status, errorMessage, breakEvenTarget, setJob, setStatus, setResult, setError,
          setBreakEvenTarget, setScenarios } = useAnalysisStore();

  const POLL_MS = 2000;

  const poll = (jobId: string) => {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        const job = await res.json();
        if (job.status === 'done') {
          clearInterval(timer);
          setResult(job.result);
          setScenarios(initScenarioCards(job.result.synth.scenarios));
          navigate('/overview');
        } else if (job.status === 'error') {
          clearInterval(timer);
          setError(job.error ?? 'Unknown error');
        } else {
          setStatus(job.status);
        }
      } catch {
        clearInterval(timer);
        setError('Network error while polling job status.');
      }
    }, POLL_MS);
  };

  const handleRun = async () => {
    if (!xlsxFiles[0]) return;

    const form = new FormData();
    form.append('xlsx', xlsxFiles[0]);
    form.append('period', period);
    form.append('year', String(year));
    form.append('company', company);
    form.append('break_even_target_ebitda', String(breakEvenTarget));
    qualFiles.forEach((f) => form.append('qual_docs', f));

    try {
      const res = await fetch('/api/run', { method: 'POST', body: form });
      const { job_id } = await res.json();
      setJob(job_id);
      poll(job_id);
    } catch {
      setError('Failed to start analysis. Is the API server running?');
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Run Analysis</h1>
        <p className="text-muted-foreground text-sm mt-1">Upload financial data and configure parameters.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>Data Files</CardTitle></CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>Excel File <span className="text-destructive">*</span></Label>
            <FileDropZone
              label=".xlsx file"
              accept=".xlsx"
              multiple={false}
              files={xlsxFiles}
              onChange={setXlsxFiles}
            />
          </div>

          <div className="space-y-2">
            <Label>
              Qual Documents{' '}
              <span className="text-muted-foreground text-xs">(optional — PDF, images)</span>
            </Label>
            <FileDropZone
              label="PDF or image files"
              accept=".pdf,.png,.jpg,.jpeg"
              multiple={true}
              files={qualFiles}
              onChange={setQualFiles}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Parameters</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Period</Label>
              <Input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="ENERO 2026" />
            </div>
            <div className="space-y-2">
              <Label>Year</Label>
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Company</Label>
            <Input value={company} onChange={(e) => setCompany(e.target.value)} />
          </div>

          <div className="space-y-3">
            <div className="flex justify-between">
              <Label>Break-Even Target EBITDA</Label>
              <span className="text-sm font-medium">{compact(breakEvenTarget)}</span>
            </div>
            <Slider
              min={0}
              max={5_000_000}
              step={100_000}
              value={[breakEvenTarget]}
              onValueChange={(v) => { if (Array.isArray(v)) setBreakEvenTarget(v[0]); }}
            />
          </div>
        </CardContent>
      </Card>

      <ProgressBar status={status} errorMessage={errorMessage} />

      <Button
        size="lg"
        className="w-full"
        onClick={handleRun}
        disabled={xlsxFiles.length === 0 || status === 'pending' || status === 'running'}
      >
        <Upload size={16} className="mr-2" />
        {status === 'running' ? 'Running Analysis…' : 'Run Analysis'}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings/dashboard"
npx tsc --noEmit
```

Expected: zero errors.

- [ ] **Step 3: Build check**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings/dashboard"
npm run build 2>&1 | tail -5
```

Expected: `✓ built in ...`

- [ ] **Step 4: Existing tests still pass**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings/dashboard"
npm test
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/josuetapiahernandez/Documents/6_Semestre/Optimizacion_No_Lineal/FLI Holdings"
git add dashboard/src/pages/Setup.tsx
git commit -m "feat(dashboard): wire FileDropZone into Setup page"
```
