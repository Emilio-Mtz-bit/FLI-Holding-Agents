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
