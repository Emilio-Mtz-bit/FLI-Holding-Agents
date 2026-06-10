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
