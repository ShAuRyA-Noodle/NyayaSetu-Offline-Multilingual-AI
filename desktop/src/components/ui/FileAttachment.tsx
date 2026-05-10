import React, { useEffect, useRef, useState } from 'react';
import { Paperclip, X, FileText, ImageIcon, AlertCircle, Upload } from 'lucide-react';

export interface FileAttachmentProps {
  files: File[];
  onChange: (files: File[]) => void;
  /** Mime types accepted, default: image/* and application/pdf. */
  accept?: string;
  /** Max number of files. Default 3. */
  maxFiles?: number;
  /** Max single-file size in bytes. Default 10MB. */
  maxSize?: number;
  disabled?: boolean;
}

const DEFAULT_ACCEPT = 'image/*,application/pdf';
const TEN_MB = 10 * 1024 * 1024;

const formatBytes = (n: number) => {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
};

const FileAttachment: React.FC<FileAttachmentProps> = ({
  files,
  onChange,
  accept = DEFAULT_ACCEPT,
  maxFiles = 3,
  maxSize = TEN_MB,
  disabled = false,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, string>>({});

  // Generate object-URL previews for image files; revoke on unmount/change.
  useEffect(() => {
    const next: Record<string, string> = {};
    files.forEach((f) => {
      if (f.type.startsWith('image/')) {
        const key = `${f.name}-${f.size}-${f.lastModified}`;
        if (previews[key]) next[key] = previews[key];
        else next[key] = URL.createObjectURL(f);
      }
    });
    // Revoke removed previews
    Object.entries(previews).forEach(([k, url]) => {
      if (!next[k]) URL.revokeObjectURL(url);
    });
    setPreviews(next);
    return () => {
      // On unmount, revoke any still-active urls
      Object.values(next).forEach((url) => URL.revokeObjectURL(url));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [files]);

  const validateAndAdd = (incoming: FileList | File[]) => {
    setError(null);
    const arr = Array.from(incoming);

    if (files.length + arr.length > maxFiles) {
      setError(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const accepted: File[] = [];
    for (const f of arr) {
      if (f.size > maxSize) {
        setError(`"${f.name}" exceeds ${formatBytes(maxSize)}`);
        return;
      }
      // Reject duplicates
      const dup = files.some(
        (x) => x.name === f.name && x.size === f.size && x.lastModified === f.lastModified
      );
      if (!dup) accepted.push(f);
    }
    if (accepted.length) onChange([...files, ...accepted]);
  };

  const removeAt = (idx: number) => {
    const next = files.slice();
    next.splice(idx, 1);
    onChange(next);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (disabled) return;
    if (e.dataTransfer?.files?.length) validateAndAdd(e.dataTransfer.files);
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onClick={() => !disabled && files.length < maxFiles && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        aria-label="Add file attachments"
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled && files.length < maxFiles) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        className={`
          relative rounded-xl border-2 border-dashed transition-all cursor-pointer p-4
          ${disabled || files.length >= maxFiles
            ? 'opacity-60 cursor-not-allowed border-white/[0.06] bg-white/[0.02]'
            : dragActive
              ? 'border-[#0D92F4]/50 bg-[#0D92F4]/[0.06]'
              : 'border-white/[0.08] bg-white/[0.02] hover:border-[#0D92F4]/30 hover:bg-[#0D92F4]/[0.03]'}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) validateAndAdd(e.target.files);
            e.target.value = '';
          }}
        />
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#0D92F4]/10 flex items-center justify-center flex-shrink-0">
            <Upload className="w-4 h-4 text-[#77CDFF]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-kora-100">
              {files.length >= maxFiles
                ? `Maximum ${maxFiles} files reached`
                : 'Attach evidence (optional)'}
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Drag &amp; drop or click — images or PDFs, up to {formatBytes(maxSize)} each, {maxFiles} files max.
            </p>
          </div>
          <Paperclip className="w-4 h-4 text-slate-500" />
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-xs text-[#F95454]">
          <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Thumbnail list */}
      {files.length > 0 && (
        <ul className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {files.map((f, idx) => {
            const key = `${f.name}-${f.size}-${f.lastModified}`;
            const isImage = f.type.startsWith('image/');
            return (
              <li
                key={key}
                className="relative rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5 flex items-center gap-2.5 group"
              >
                <div className="w-10 h-10 rounded-lg overflow-hidden bg-white/[0.04] flex items-center justify-center flex-shrink-0 border border-white/[0.04]">
                  {isImage && previews[key] ? (
                    <img
                      src={previews[key]}
                      alt={f.name}
                      className="w-full h-full object-cover"
                    />
                  ) : f.type === 'application/pdf' ? (
                    <FileText className="w-5 h-5 text-[#F95454]" />
                  ) : (
                    <ImageIcon className="w-5 h-5 text-slate-400" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-kora-100 truncate" title={f.name}>{f.name}</p>
                  <p className="text-[10px] text-slate-500">{formatBytes(f.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeAt(idx)}
                  aria-label={`Remove ${f.name}`}
                  className="flex-shrink-0 p-1 rounded-md text-slate-400 hover:text-[#F95454] hover:bg-white/[0.06] transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};

export default FileAttachment;
