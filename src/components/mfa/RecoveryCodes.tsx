import React, { useState } from 'react';
import { Copy, Download, Check, ArrowRight } from 'lucide-react';
import Button from '../ui/Button';
import { useT } from '../../i18n';

interface RecoveryCodesProps {
  codes: string[];
  /** Called once the person says the codes are kept somewhere safe. */
  onDone: () => void;
  doneLabel: string;
}

/**
 * Recovery codes, shown once (#44): the server keeps only their hashes, so
 * this is the only chance to keep them. Nothing here is stored in the
 * browser; copy and download hand them to the person and nowhere else.
 */
export default function RecoveryCodes({ codes, onDone, doneLabel }: RecoveryCodesProps) {
  const t = useT();
  const [kept, setKept] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = codes.join('\n') + '\n';

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      // No clipboard (an insecure context, a refusal): the download still works.
      setCopied(false);
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'dixpertia-recovery-codes.txt';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-on-surface-variant">{t('auth.mfa.codesIntro')}</p>
      <ul
        aria-label={t('auth.mfa.codesTitle')}
        className="grid grid-cols-2 gap-x-4 gap-y-1.5 rounded-xl border border-outline-variant bg-surface-container-low p-4 font-mono text-sm"
      >
        {codes.map((code) => <li key={code}>{code}</li>)}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={copy}>
          {copied ? <Check className="w-4 h-4" aria-hidden="true" /> : <Copy className="w-4 h-4" aria-hidden="true" />}
          {copied ? t('auth.mfa.copied') : t('auth.mfa.copy')}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={download}>
          <Download className="w-4 h-4" aria-hidden="true" />
          {t('auth.mfa.download')}
        </Button>
      </div>
      <label className="flex items-start gap-2 text-sm cursor-pointer">
        <input type="checkbox" className="mt-0.5" checked={kept} onChange={(e) => setKept(e.target.checked)} />
        {t('auth.mfa.codesKept')}
      </label>
      <Button type="button" onClick={onDone} disabled={!kept} className="self-start">
        {doneLabel}
        <ArrowRight className="w-4 h-4" aria-hidden="true" />
      </Button>
    </div>
  );
}
