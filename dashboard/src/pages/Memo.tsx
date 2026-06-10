import { useAnalysisStore } from '@/store/analysis';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

export default function Memo() {
  const result = useAnalysisStore((s) => s.result);
  if (!result) return <div className="p-8 text-muted-foreground">No analysis loaded. Run setup first.</div>;

  const html = result.synth.memo_html;
  const period = result.period;

  const handleDownload = () => {
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `memo_${period.replace(/\s+/g, '_')}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-3 border-b">
        <h1 className="text-lg font-semibold">Memo — {period}</h1>
        <Button variant="outline" size="sm" onClick={handleDownload}>
          <Download size={14} className="mr-1" /> Download HTML
        </Button>
      </div>
      <iframe
        srcDoc={html}
        className="flex-1 w-full border-0"
        title="Analysis Memo"
        sandbox="allow-same-origin"
      />
    </div>
  );
}
