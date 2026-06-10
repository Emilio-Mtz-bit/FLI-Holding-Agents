import { Progress } from '@/components/ui/progress';
import type { JobStatus } from '@/types/analysis';

const STEPS = ['Loading', 'Quant', 'Qual', 'Synth', 'Done'];

interface Props {
  status: JobStatus;
  errorMessage?: string | null;
}

export default function ProgressBar({ status, errorMessage }: Props) {
  const idx =
    status === 'idle' ? -1
    : status === 'pending' ? 0
    : status === 'running' ? 2
    : status === 'done' ? 4
    : 4;
  const pct = status === 'idle' ? 0 : ((idx + 1) / STEPS.length) * 100;

  if (status === 'idle') return null;

  return (
    <div className="space-y-2">
      <Progress value={pct} className="h-2" />
      <div className="flex justify-between text-xs text-muted-foreground">
        {STEPS.map((s, i) => (
          <span key={s} className={i <= idx ? 'text-primary font-medium' : ''}>{s}</span>
        ))}
      </div>
      {status === 'error' && (
        <p className="text-sm text-destructive">{errorMessage}</p>
      )}
    </div>
  );
}
