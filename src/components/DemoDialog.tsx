import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Check, Info } from 'lucide-react';
import * as api from '../api';
import type { Demo, DemoInput, DemoService } from '../api';
import { useT, type MessageKey } from '../i18n';
import { embedUrl, isDriveImage, parseVideoLink } from '../demoLinks';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Select, Textarea } from './ui/Field';

/**
 * Add or edit a demo video (#233), as designed in design/demo-videos.
 *
 * The admin pastes a link; the form names its source as soon as it is
 * recognised and plays it, so the admin can check it is the right video
 * before the website shows it. Both languages are required, each in its own
 * tab, and each tab says in words whether it is complete. The server checks
 * everything again and answers in the interface's language.
 */

type Lang = 'fr' | 'en';
const LANGS: Lang[] = ['fr', 'en'];
const TITLE_MAX = 80;
const DESCRIPTION_MAX = 300;
export const SERVICES: DemoService[] = ['cloud', 'security', 'software'];
export const SERVICE_LABEL: Record<DemoService, MessageKey> = {
  cloud: 'demos.service.cloud',
  security: 'demos.service.security',
  software: 'demos.service.software',
};
export const PROVIDER_LABEL: Record<api.DemoProvider, MessageKey> = {
  drive: 'demos.provider.drive',
  youtube: 'demos.provider.youtube',
  vimeo: 'demos.provider.vimeo',
};

// A new demo is published unless the admin says otherwise (decided on #231).
const EMPTY: DemoInput = {
  title_fr: '', title_en: '', description_fr: '', description_en: '',
  video_url: '', thumbnail_url: '', service: null, published: true,
};

function fromDemo(demo: Demo): DemoInput {
  return {
    title_fr: demo.title_fr, title_en: demo.title_en,
    description_fr: demo.description_fr, description_en: demo.description_en,
    video_url: demo.video_url, thumbnail_url: demo.thumbnail_url ?? '',
    service: demo.service, published: demo.published,
  };
}

type Errors = Partial<Record<'video_url' | 'thumbnail_url' | 'title_fr' | 'title_en' | 'description_fr' | 'description_en', string>>;

export default function DemoDialog({ open, demo, onClose, onSaved }: {
  open: boolean;
  /** The demo to edit, or null for a new one. */
  demo: Demo | null;
  onClose: () => void;
  onSaved: (saved: Demo) => void;
}) {
  const t = useT();
  const [form, setForm] = useState<DemoInput>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [tab, setTab] = useState<Lang>('fr');
  const tabRefs = useRef<Record<Lang, HTMLButtonElement | null>>({ fr: null, en: null });
  const bodyRef = useRef<HTMLFormElement>(null);
  const baseId = useId();

  // A fresh form each time the dialog opens.
  useEffect(() => {
    if (!open) return;
    setForm(demo ? fromDemo(demo) : EMPTY);
    setErrors({});
    setServerError(null);
    setSaving(false);
    setTab('fr');
    // The first field takes focus, after the dialog has moved it to its close button.
    window.setTimeout(() => bodyRef.current?.querySelector<HTMLInputElement>('input')?.focus(), 0);
  }, [open, demo]);

  const link = useMemo(() => parseVideoLink(form.video_url), [form.video_url]);
  const linkTyped = form.video_url.trim() !== '';
  // Shown as soon as the field holds text it cannot read, as designed.
  const linkError = errors.video_url ?? (linkTyped && !link ? t('demos.form.linkUnknown') : undefined);
  const imageTyped = form.thumbnail_url.trim() !== '';
  const imageError = errors.thumbnail_url ?? (imageTyped && !isDriveImage(form.thumbnail_url) ? t('demos.form.imageUnknown') : undefined);

  const complete = (lang: Lang) => form[`title_${lang}`].trim() !== '' && form[`description_${lang}`].trim() !== '';

  const set = (field: keyof DemoInput) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const value = e.target.value;
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validate = (): Errors => {
    const found: Errors = {};
    if (!linkTyped) found.video_url = t('demos.form.linkRequired');
    else if (!link) found.video_url = t('demos.form.linkUnknown');
    if (imageTyped && !isDriveImage(form.thumbnail_url)) found.thumbnail_url = t('demos.form.imageUnknown');
    for (const lang of LANGS) {
      if (!form[`title_${lang}`].trim()) found[`title_${lang}`] = t(`demos.form.titleMissing.${lang}`);
      if (!form[`description_${lang}`].trim()) found[`description_${lang}`] = t(`demos.form.descriptionMissing.${lang}`);
    }
    return found;
  };

  const errorCount = Object.values(errors).filter(Boolean).length;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving) return;
    const found = validate();
    setErrors(found);
    setServerError(null);
    if (Object.keys(found).length > 0) {
      // Save goes to the first language with a missing field.
      const firstMissing = LANGS.find((lang) => found[`title_${lang}`] || found[`description_${lang}`]);
      if (firstMissing) setTab(firstMissing);
      return;
    }
    setSaving(true);
    const body: DemoInput = {
      ...form,
      title_fr: form.title_fr.trim(), title_en: form.title_en.trim(),
      description_fr: form.description_fr.trim(), description_en: form.description_en.trim(),
      video_url: form.video_url.trim(), thumbnail_url: form.thumbnail_url.trim(),
    };
    try {
      const saved = demo ? await api.demos.update(demo.id, body) : await api.demos.create(body);
      onSaved(saved);
    } catch (err) {
      // A refusal the server explains (a link it does not accept) is shown as
      // it says it; anything else is the designed "nothing was lost" message.
      setServerError(err instanceof api.ApiError && err.status < 500 ? err.message : t('demos.form.couldNotSave'));
    } finally {
      setSaving(false);
    }
  };

  // WAI-ARIA tabs: arrows, Home and End move between the two, focus follows.
  const onTabKey = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const index = LANGS.indexOf(tab);
    const next = {
      ArrowRight: LANGS[(index + 1) % LANGS.length],
      ArrowLeft: LANGS[(index + LANGS.length - 1) % LANGS.length],
      Home: LANGS[0],
      End: LANGS[LANGS.length - 1],
    }[e.key];
    if (!next) return;
    e.preventDefault();
    setTab(next);
    tabRefs.current[next]?.focus();
  };

  const langName = (lang: Lang) => t(`demos.form.lang.${lang}`);
  const title = form[`title_${tab}`];
  const description = form[`description_${tab}`];

  return (
    <Dialog
      open={open}
      // Escape and the close button do nothing while saving.
      onClose={() => { if (!saving) onClose(); }}
      title={t(demo ? 'demos.form.editTitle' : 'demos.form.addTitle')}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            {t('demos.form.cancel')}
          </Button>
          <Button type="submit" form={`${baseId}-form`} loading={saving}>
            {t('demos.form.save')}
          </Button>
        </>
      }
    >
      <form ref={bodyRef} id={`${baseId}-form`} onSubmit={submit} className="flex flex-col gap-6" noValidate>
        {errorCount > 0 && <FormAlert>{t('demos.form.attention', { count: errorCount })}</FormAlert>}

        {/* 1. The video link, its source and a player to check it */}
        <div className="flex flex-col gap-3">
          <Field label={t('demos.form.link')} hint={t('demos.form.linkHint')} error={linkError}>
            {({ id, describedBy, invalid }) => (
              <div className="relative">
                <Input
                  id={id}
                  type="url"
                  inputMode="url"
                  autoComplete="off"
                  spellCheck={false}
                  maxLength={500}
                  value={form.video_url}
                  onChange={set('video_url')}
                  invalid={invalid}
                  aria-describedby={describedBy}
                  className={`font-mono text-body-sm ${link ? 'pr-32' : ''}`}
                />
                {link && (
                  <span className="pointer-events-none absolute right-2 top-1/2 inline-flex -translate-y-1/2 items-center gap-1.5 rounded-full bg-surface-container-high px-2.5 py-0.5 font-mono text-[11px] text-on-surface">
                    <Check className="h-3 w-3" aria-hidden="true" />
                    <span className="sr-only">{t('demos.form.source', { source: t(PROVIDER_LABEL[link.provider]) })}</span>
                    <span aria-hidden="true">{t(PROVIDER_LABEL[link.provider])}</span>
                  </span>
                )}
              </div>
            )}
          </Field>
          {link && (
            <div className="flex flex-col gap-4 rounded-xl bg-surface-container-low p-4 sm:flex-row sm:items-center">
              <div className="aspect-video w-full shrink-0 overflow-hidden rounded-lg bg-ink sm:w-[220px]">
                <iframe
                  key={embedUrl(link)}
                  src={embedUrl(link)}
                  title={t('demos.form.playerTitle', { title: form[`title_${tab}`].trim() || t(PROVIDER_LABEL[link.provider]) })}
                  className="h-full w-full border-0"
                  allow="autoplay; fullscreen"
                  allowFullScreen
                  loading="lazy"
                  referrerPolicy="strict-origin-when-cross-origin"
                />
              </div>
              <div className="flex flex-col gap-1">
                <p className="m-0 text-body-sm font-semibold text-on-surface">{t('demos.form.previewQuestion')}</p>
                <p className="m-0 text-body-sm text-on-surface-variant">{t('demos.form.previewNote')}</p>
              </div>
            </div>
          )}
        </div>

        {/* 2. The preview image, optional */}
        <Field
          label={t('demos.form.image')}
          labelAside={<Optional />}
          hint={imageTyped ? t('demos.form.imageHint') : undefined}
          error={imageError}
        >
          {({ id, describedBy, invalid }) => (
            <>
              <Input
                id={id}
                type="url"
                inputMode="url"
                autoComplete="off"
                spellCheck={false}
                maxLength={500}
                value={form.thumbnail_url}
                onChange={set('thumbnail_url')}
                invalid={invalid}
                aria-describedby={[describedBy, imageTyped ? undefined : `${baseId}-auto`].filter(Boolean).join(' ') || undefined}
                className="font-mono text-body-sm"
              />
              {!imageTyped && (
                <p id={`${baseId}-auto`} className="m-0 flex items-start gap-2 text-xs text-on-surface-variant">
                  <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>
                    <span className="font-semibold text-on-surface">{t('demos.form.imageAuto')}</span>{' '}
                    {t('demos.form.imageAutoHint')}
                  </span>
                </p>
              )}
            </>
          )}
        </Field>

        {/* 3. The content, one tab per language */}
        <fieldset className="m-0 flex min-w-0 flex-col gap-3 border-0 p-0">
          <legend className="mb-1.5 p-0 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
            {t('demos.form.content')}
          </legend>
          <div role="tablist" aria-label={t('demos.form.content')} className="grid grid-cols-2 gap-1 rounded-lg bg-surface-container-low p-1">
            {LANGS.map((lang) => {
              const selected = tab === lang;
              const ok = complete(lang);
              // Red once Save has flagged this language; before that, a plain "Missing".
              const flagged = Boolean(errors[`title_${lang}`] || errors[`description_${lang}`]);
              return (
                <button
                  key={lang}
                  ref={(el) => { tabRefs.current[lang] = el; }}
                  type="button"
                  role="tab"
                  id={`${baseId}-tab-${lang}`}
                  aria-selected={selected}
                  aria-controls={`${baseId}-panel-${lang}`}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => setTab(lang)}
                  onKeyDown={onTabKey}
                  className={`flex min-h-11 cursor-pointer flex-col items-start justify-center gap-0.5 rounded-md px-3 py-1.5 text-left text-body-sm transition-colors sm:flex-row sm:items-center sm:justify-between sm:gap-2 ${
                    selected ? 'bg-surface-container-lowest font-semibold text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  <span>
                    <span className="mr-1.5 font-mono text-[11px] uppercase">{lang}</span>
                    {langName(lang)}
                  </span>
                  {ok ? (
                    <span className="inline-flex items-center gap-1 text-xs text-on-surface-variant">
                      <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('demos.form.complete')}
                    </span>
                  ) : (
                    <span className={`inline-flex items-center gap-1 text-xs ${flagged ? 'text-error' : 'text-on-surface-variant'}`}>
                      <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
                      {t('demos.form.missing')}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <div
            role="tabpanel"
            id={`${baseId}-panel-${tab}`}
            aria-labelledby={`${baseId}-tab-${tab}`}
            lang={tab}
            className="flex flex-col gap-4"
          >
            <Field
              key={`title-${tab}`}
              label={t('demos.form.titleLabel', { lang: tab.toUpperCase() })}
              labelAside={<Counter count={title.length} max={TITLE_MAX} />}
              error={errors[`title_${tab}`]}
            >
              {({ id, describedBy, invalid }) => (
                <Input id={id} maxLength={TITLE_MAX} value={title} onChange={set(`title_${tab}`)} invalid={invalid} aria-describedby={describedBy} />
              )}
            </Field>
            <Field
              key={`description-${tab}`}
              label={t('demos.form.descriptionLabel', { lang: tab.toUpperCase() })}
              labelAside={<Counter count={description.length} max={DESCRIPTION_MAX} />}
              error={errors[`description_${tab}`]}
            >
              {({ id, describedBy, invalid }) => (
                <Textarea id={id} rows={4} maxLength={DESCRIPTION_MAX} value={description} onChange={set(`description_${tab}`)} invalid={invalid} aria-describedby={describedBy} />
              )}
            </Field>
          </div>
          <p className="m-0 text-xs text-on-surface-variant">{t('demos.form.languagesHint')}</p>
        </fieldset>

        {/* 4. Service and 5. status */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <Field label={t('demos.form.service')} labelAside={<Optional />}>
            {({ id }) => (
              <Select
                id={id}
                value={form.service ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, service: (e.target.value || null) as DemoService | null }))}
              >
                <option value="">{t('demos.service.none')}</option>
                {SERVICES.map((s) => (
                  <option key={s} value={s}>{t(SERVICE_LABEL[s])}</option>
                ))}
              </Select>
            )}
          </Field>
          <fieldset className="m-0 flex min-w-0 flex-col gap-1.5 border-0 p-0" aria-describedby={`${baseId}-status-hint`}>
            <legend className="mb-1.5 p-0 font-mono text-[11px] font-medium uppercase tracking-[0.08em] text-on-surface-variant">
              {t('demos.form.status')}
            </legend>
            <div className="grid grid-cols-2 gap-2">
              {[true, false].map((published) => {
                const checked = form.published === published;
                return (
                  <label
                    key={String(published)}
                    className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 text-body-sm ${
                      checked ? 'border-on-surface font-semibold text-on-surface' : 'border-outline-variant text-on-surface-variant'
                    }`}
                  >
                    <input
                      type="radio"
                      name={`${baseId}-status`}
                      className="h-4 w-4 accent-primary cursor-pointer"
                      checked={checked}
                      onChange={() => setForm((f) => ({ ...f, published }))}
                    />
                    {t(published ? 'demos.published' : 'demos.hidden')}
                  </label>
                );
              })}
            </div>
            <p id={`${baseId}-status-hint`} className="m-0 text-xs text-on-surface-variant">{t('demos.form.statusHint')}</p>
          </fieldset>
        </div>

        {serverError && <FormAlert>{serverError}</FormAlert>}
      </form>
    </Dialog>
  );
}

function Counter({ count, max }: { count: number; max: number }) {
  const t = useT();
  return (
    <span className="font-mono text-[11px] text-on-surface-variant" aria-live="polite">
      {t('demos.form.counter', { count, max })}
    </span>
  );
}

function Optional() {
  const t = useT();
  return <span className="font-mono text-[11px] text-on-surface-variant">{t('demos.form.optional')}</span>;
}
