import { useCallback, useEffect, useState } from 'react';
import { ArrowDown, ArrowUp, Check, EyeOff, Eye, Pencil, Play, Plus, Trash2 } from 'lucide-react';
import * as api from '../api';
import type { Demo } from '../api';
import { useLocale, useT } from '../i18n';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import Button from './ui/Button';
import { useConfirm, useToast } from './ui/feedback';
import DemoDialog, { PROVIDER_LABEL, SERVICE_LABEL } from './DemoDialog';

/**
 * The website's demo videos (#233), admin only, as designed in
 * design/demo-videos. Order, publish / hide and delete act at once; the order
 * is saved optimistically and put back if the server refuses it. Under 760px
 * the table becomes cards, with 44px touch targets and no sideways scroll.
 */

export default function DemosView() {
  const t = useT();
  const locale = useLocale();
  const toast = useToast();
  const confirm = useConfirm();
  const [demos, setDemos] = useState<Demo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Demo | null>(null);
  const [open, setOpen] = useState(false);
  const [announcement, setAnnouncement] = useState('');

  const load = useCallback(() => {
    setError(null);
    api.demos
      .list()
      .then(setDemos)
      .catch((err) => setError(err instanceof Error ? err.message : t('demos.couldNotLoad')));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(load, [load]);

  const titleOf = (demo: Demo) => (locale === 'en' ? demo.title_en : demo.title_fr);

  const start = (demo: Demo | null) => {
    setEditing(demo);
    setOpen(true);
  };

  const saved = (demo: Demo) => {
    setOpen(false);
    setDemos((list) => {
      if (!list) return [demo];
      return list.some((d) => d.id === demo.id) ? list.map((d) => (d.id === demo.id ? demo : d)) : [...list, demo];
    });
    toast(t('demos.form.saved', { title: titleOf(demo) }));
  };

  // Swap with the neighbour, save the whole order, and put it back on failure.
  const move = async (demo: Demo, step: -1 | 1, button: HTMLButtonElement) => {
    if (!demos) return;
    const from = demos.findIndex((d) => d.id === demo.id);
    const to = from + step;
    if (to < 0 || to >= demos.length) return;
    const before = demos;
    const after = [...demos];
    [after[from], after[to]] = [after[to], after[from]];
    setDemos(after);
    setAnnouncement(t('demos.moved', { title: titleOf(demo), position: to + 1, count: after.length }));
    // The pressed arrow moves with its row. At the top or the bottom it becomes
    // disabled, so focus goes to the other arrow of the same row.
    window.setTimeout(() => {
      if (button.disabled) {
        const other = button.parentElement?.querySelector<HTMLButtonElement>('button[data-move]:not([disabled])');
        other?.focus();
      }
    }, 0);
    try {
      setDemos(await api.demos.reorder(after.map((d) => d.id)));
    } catch {
      setDemos(before);
      setAnnouncement('');
      toast(t('demos.couldNotMove'), 'error');
    }
  };

  const togglePublished = async (demo: Demo) => {
    try {
      const updated = await api.demos.update(demo.id, { published: !demo.published });
      setDemos((list) => list?.map((d) => (d.id === updated.id ? updated : d)) ?? null);
      toast(t(updated.published ? 'demos.nowPublished' : 'demos.nowHidden', { title: titleOf(updated) }));
    } catch (err) {
      toast(err instanceof api.ApiError ? err.message : t('demos.couldNotUpdate'), 'error');
    }
  };

  const remove = async (demo: Demo) => {
    const ok = await confirm({
      title: t('demos.deleteTitle'),
      message: t('demos.deleteMessage', { title: titleOf(demo) }),
      confirmLabel: t('demos.delete'),
      tone: 'danger',
    });
    if (!ok || !demos) return;
    const index = demos.findIndex((d) => d.id === demo.id);
    try {
      await api.demos.remove(demo.id);
      const rest = demos.filter((d) => d.id !== demo.id);
      setDemos(rest);
      toast(t('demos.deleted'));
      // Focus goes to the next row's Edit button, or to "New demo" when none is left.
      window.setTimeout(() => {
        const next = rest[Math.min(index, rest.length - 1)];
        const candidates = next
          ? document.querySelectorAll<HTMLButtonElement>(`[data-edit="${next.id}"]`)
          : document.querySelectorAll<HTMLButtonElement>('[data-new-demo], [data-first-demo]');
        // The table and the cards both exist; only one of them is displayed.
        Array.from(candidates).find((b) => b.offsetParent !== null)?.focus();
      }, 0);
    } catch (err) {
      toast(err instanceof api.ApiError ? err.message : t('demos.couldNotDelete'), 'error');
    }
  };

  const published = demos?.filter((d) => d.published).length ?? 0;
  const empty = demos !== null && demos.length === 0;

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="flex flex-col items-stretch justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-h1 font-black tracking-tight text-on-surface md:text-display">{t('demos.title')}</h1>
          <p className="mt-1 text-body-lg text-on-surface-variant">{t('demos.intro')}</p>
        </div>
        {!empty && (
          <Button data-new-demo onClick={() => start(null)} className="w-full md:w-auto">
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t('demos.new')}
          </Button>
        )}
      </div>

      {/* The result of a move, for screen readers. */}
      <p className="sr-only" aria-live="polite">{announcement}</p>

      {error ? (
        <Table caption={t('demos.caption')}>
          <TBody>
            <TableState kind="error" colSpan={1} message={error} />
          </TBody>
        </Table>
      ) : demos === null ? (
        <Table caption={t('demos.caption')}>
          <TBody>
            <TableState kind="loading" colSpan={1} title={t('demos.loading')} />
          </TBody>
        </Table>
      ) : empty ? (
        <EmptyState onAdd={() => start(null)} />
      ) : (
        <>
          {/* Desktop and tablet: the table */}
          <div className="hidden min-[760px]:block">
            <Table caption={t('demos.caption')}>
              <THead>
                <Th>{t('demos.col.order')}</Th>
                <Th>{t('demos.col.preview')}</Th>
                <Th>{t('demos.col.title')}</Th>
                <Th>{t('demos.col.service')}</Th>
                <Th>{t('demos.col.status')}</Th>
                <Th numeric><span className="sr-only">{t('demos.col.actions')}</span></Th>
              </THead>
              <TBody>
                {demos.map((demo, index) => (
                  <Tr key={demo.id}>
                    <Td>
                      <div className="flex items-center gap-2">
                        <span className="w-6 font-mono text-body-sm tabular-nums text-on-surface-variant">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                        <MoveButtons demo={demo} index={index} count={demos.length} title={titleOf(demo)} onMove={move} />
                      </div>
                    </Td>
                    <Td><Thumbnail demo={demo} /></Td>
                    <Td className="min-w-[14rem]">
                      <div className="font-semibold text-on-surface">{titleOf(demo)}</div>
                      <div className="font-mono text-[11px] text-on-surface-variant">{t(PROVIDER_LABEL[demo.provider])}</div>
                    </Td>
                    <Td><ServicePill demo={demo} /></Td>
                    <Td className="whitespace-nowrap"><StatusBadge published={demo.published} /></Td>
                    <Td numeric>
                      <RowActions demo={demo} title={titleOf(demo)} onEdit={start} onToggle={togglePublished} onDelete={remove} />
                    </Td>
                  </Tr>
                ))}
              </TBody>
            </Table>
          </div>

          {/* Phone: one card per demo */}
          <ul className="m-0 flex list-none flex-col gap-3 p-0 min-[760px]:hidden" aria-label={t('demos.caption')}>
            {demos.map((demo, index) => (
              <li key={demo.id} className="rounded-xl border border-outline-variant bg-surface-container-lowest p-3">
                <div className="flex gap-3">
                  <Thumbnail demo={demo} />
                  <div className="flex min-w-0 flex-col gap-2">
                    <span className="font-semibold text-on-surface [overflow-wrap:anywhere]">{titleOf(demo)}</span>
                    <div className="flex flex-wrap gap-2">
                      <StatusBadge published={demo.published} />
                      {demo.service && <ServicePill demo={demo} />}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-outline-variant pt-3">
                  <MoveButtons demo={demo} index={index} count={demos.length} title={titleOf(demo)} onMove={move} large />
                  <span className="font-mono text-body-sm tabular-nums text-on-surface-variant">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="ml-auto flex items-center gap-1">
                    <RowActions demo={demo} title={titleOf(demo)} onEdit={start} onToggle={togglePublished} onDelete={remove} large />
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <p className="m-0 text-body-sm text-on-surface-variant">
            {t('demos.count', { count: demos.length })} · {t('demos.onSite', { count: published })}
          </p>
        </>
      )}

      <DemoDialog open={open} demo={editing} onClose={() => setOpen(false)} onSaved={saved} />
    </div>
  );
}

function MoveButtons({ demo, index, count, title, onMove, large = false }: {
  demo: Demo;
  index: number;
  count: number;
  title: string;
  onMove: (demo: Demo, step: -1 | 1, button: HTMLButtonElement) => void;
  large?: boolean;
}) {
  const t = useT();
  const size = large ? 'h-11 w-11' : 'h-8 w-8';
  const style = `inline-flex ${size} cursor-pointer items-center justify-center rounded-md border border-outline-variant text-on-surface transition-colors hover:bg-surface-container disabled:cursor-not-allowed disabled:opacity-35`;
  return (
    <span className="inline-flex gap-1">
      <button
        type="button"
        data-move="up"
        className={style}
        disabled={index === 0}
        aria-label={t('demos.moveUp', { title })}
        onClick={(e) => onMove(demo, -1, e.currentTarget)}
      >
        <ArrowUp className="h-4 w-4" aria-hidden="true" />
      </button>
      <button
        type="button"
        data-move="down"
        className={style}
        disabled={index === count - 1}
        aria-label={t('demos.moveDown', { title })}
        onClick={(e) => onMove(demo, 1, e.currentTarget)}
      >
        <ArrowDown className="h-4 w-4" aria-hidden="true" />
      </button>
    </span>
  );
}

function RowActions({ demo, title, onEdit, onToggle, onDelete, large = false }: {
  demo: Demo;
  title: string;
  onEdit: (demo: Demo) => void;
  onToggle: (demo: Demo) => void;
  onDelete: (demo: Demo) => void;
  /** The phone cards: 44px targets, Edit and Hide / Publish with their words. */
  large?: boolean;
}) {
  const t = useT();
  const toggleLabel = t(demo.published ? 'demos.hideLabel' : 'demos.publishLabel', { title });
  const ToggleIcon = demo.published ? EyeOff : Eye;
  if (!large) {
    // In the table the three actions are compact icon buttons, so the row fits
    // at 1440 without sideways scroll (decided on #231). Each one is named by
    // its title, and the same words show as a tooltip.
    const icon = 'inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-on-surface transition-colors hover:bg-surface-container';
    return (
      <span className="inline-flex flex-nowrap items-center justify-end gap-1">
        <button type="button" className={icon} data-edit={demo.id} onClick={() => onEdit(demo)}
          aria-label={t('demos.editLabel', { title })} title={t('demos.edit')}>
          <Pencil className="h-4 w-4" aria-hidden="true" />
        </button>
        <button type="button" className={icon} onClick={() => onToggle(demo)}
          aria-label={toggleLabel} title={t(demo.published ? 'demos.hide' : 'demos.publish')}>
          <ToggleIcon className="h-4 w-4" aria-hidden="true" />
        </button>
        <button type="button" className={`${icon} text-error hover:bg-error-container`} onClick={() => onDelete(demo)}
          aria-label={t('demos.deleteLabel', { title })} title={t('demos.delete')}>
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </span>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-center justify-end gap-1">
      <Button variant="ghost" size="sm" className="min-h-11" data-edit={demo.id} onClick={() => onEdit(demo)} aria-label={t('demos.editLabel', { title })}>
        <Pencil className="h-4 w-4" aria-hidden="true" />
        {t('demos.edit')}
      </Button>
      <Button variant="ghost" size="sm" className="min-h-11" onClick={() => onToggle(demo)} aria-label={toggleLabel}>
        <ToggleIcon className="h-4 w-4" aria-hidden="true" />
        {t(demo.published ? 'demos.hide' : 'demos.publish')}
      </Button>
      <Button variant="ghost" size="sm" className="min-h-11 w-11 px-0 text-error hover:text-error" onClick={() => onDelete(demo)}
        aria-label={t('demos.deleteLabel', { title })}>
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </Button>
    </span>
  );
}

function StatusBadge({ published }: { published: boolean }) {
  const t = useT();
  return published ? (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-success/35 bg-success-container px-2.5 py-0.5 text-body-sm font-semibold text-success">
      <Check className="h-3.5 w-3.5" aria-hidden="true" />
      {t('demos.published')}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-outline px-2.5 py-0.5 text-body-sm text-on-surface-variant">
      <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
      {t('demos.hidden')}
    </span>
  );
}

function ServicePill({ demo }: { demo: Demo }) {
  const t = useT();
  if (!demo.service) return <span className="text-on-surface-variant">—</span>;
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-full border border-outline-variant px-2.5 py-0.5 text-body-sm text-on-surface">
      {t(SERVICE_LABEL[demo.service])}
    </span>
  );
}

/**
 * The stored preview, loaded with the admin's token: an <img src> cannot send
 * it, and the page never loads images from the video host. A demo whose
 * preview could not be fetched shows a dark panel with the play mark.
 */
function Thumbnail({ demo }: { demo: Demo }) {
  const t = useT();
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!demo.preview_image) {
      setUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    api.demos
      .preview(demo.preview_image)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => { if (!cancelled) setUrl(null); });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [demo.preview_image]);

  return (
    <div className="relative aspect-video w-[120px] shrink-0 overflow-hidden rounded-md bg-ink">
      {url ? (
        <img src={url} alt="" className="h-full w-full object-cover" />
      ) : (
        <span className="flex h-full w-full items-center justify-center text-paper/70" aria-hidden="true">
          <Play className="h-5 w-5" />
        </span>
      )}
      {!demo.thumbnail_url && (
        <span className="absolute left-1 top-1 rounded-sm bg-ink px-1 font-mono text-[8px] font-semibold uppercase tracking-[0.08em] text-paper">
          <span aria-hidden="true">{t('demos.auto')}</span>
          <span className="sr-only">{t('demos.autoLabel')}</span>
        </span>
      )}
    </div>
  );
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  const t = useT();
  return (
    <section className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-outline bg-surface-container-lowest px-6 py-12 text-center">
      <div className="flex aspect-video w-44 items-center justify-center rounded-lg bg-ink" aria-hidden="true">
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-lime text-ink">
          <Play className="h-5 w-5 translate-x-px" />
        </span>
      </div>
      <h2 className="m-0 text-h3 font-semibold text-on-surface">{t('demos.emptyTitle')}</h2>
      <p className="m-0 max-w-prose text-body-sm text-on-surface-variant">{t('demos.emptyMessage')}</p>
      <Button onClick={onAdd} data-first-demo>
        <Plus className="h-4 w-4" aria-hidden="true" />
        {t('demos.emptyAction')}
      </Button>
      <p className="m-0 font-mono text-[11px] text-on-surface-variant">{t('demos.emptyNote')}</p>
    </section>
  );
}
