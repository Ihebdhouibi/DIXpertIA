import React, { useMemo, useState } from 'react';
import { Pencil, Plus } from 'lucide-react';
import * as api from '../api';
import type { Client } from '../types';
import { useT } from '../i18n';
import { Table, THead, Th, TBody, Tr, Td, TableState } from './ui/Table';
import { SearchField } from './ui/TableControls';
import Avatar from './ui/Avatar';
import Button from './ui/Button';
import Dialog from './ui/Dialog';
import { Field, FormAlert, Input, Select, Textarea } from './ui/Field';
import { useToast } from './ui/feedback';
import { useDataStatus } from '../dataStatus';

/**
 * Clients (#192): the people and companies we invoice, and the language their
 * invoices print in (#135). Admin and accountant. The server validates and
 * trims every field and refuses a duplicate name; this form only checks what
 * it can say early (a name, an e-mail's shape).
 */

type Locale = 'fr' | 'en';
const EMPTY = { nom: '', email: '', telephone: '', adresse: '', locale: 'fr' as Locale };
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

export default function ClientsView({ clients, onChanged }: { clients: Client[]; onChanged: () => Promise<void> }) {
  const t = useT();
  const toast = useToast();
  const status = useDataStatus();
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState<Client | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? clients.filter((c) => c.nom.toLowerCase().includes(q) || (c.email ?? '').toLowerCase().includes(q)) : clients;
  }, [clients, query]);

  const start = (client: Client | null) => {
    setEditing(client);
    setForm(client
      ? { nom: client.nom, email: client.email ?? '', telephone: client.telephone ?? '', adresse: client.adresse ?? '', locale: client.locale ?? 'fr' }
      : EMPTY);
    setError(null);
    setOpen(true);
  };

  const set = (field: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.nom.trim()) return setError(t('invoices.clients.form.nameRequired'));
    if (form.email.trim() && !EMAIL.test(form.email.trim())) return setError(t('invoices.clients.form.emailInvalid'));
    setSaving(true);
    setError(null);
    try {
      const saved = editing ? await api.clients.update(editing.id, form) : await api.clients.create(form);
      await onChanged();
      toast(t(editing ? 'invoices.clients.updated' : 'invoices.clients.created', { name: saved.nom }));
      setOpen(false);
    } catch (err) {
      // The server's message, in the UI's language (#135): a duplicate name says which.
      setError(err instanceof api.ApiError ? err.message : t('invoices.clients.couldNotSave'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-h1 font-black tracking-tight text-on-surface md:text-display">{t('invoices.clients.title')}</h1>
          <p className="mt-1 text-body-lg text-on-surface-variant">{t('invoices.clients.intro')}</p>
        </div>
        <Button onClick={() => start(null)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('invoices.clients.new')}
        </Button>
      </div>

      <SearchField
        label={t('invoices.clients.search')}
        placeholder={t('invoices.clients.searchPlaceholder')}
        value={query}
        onChange={setQuery}
        className="md:max-w-sm"
      />

      <Table caption={t('invoices.clients.title')}>
        <THead>
          <Th>{t('invoices.clients.col.name')}</Th>
          <Th>{t('invoices.clients.col.contact')}</Th>
          <Th>{t('invoices.clients.col.language')}</Th>
          <Th numeric>
            <span className="sr-only">{t('invoices.clients.col.actions')}</span>
          </Th>
        </THead>
        <TBody>
          {shown.length > 0 ? (
            shown.map((c) => (
              <Tr key={c.id}>
                <Td>
                  <div className="flex items-center gap-3">
                    <Avatar name={c.nom} size="sm" shape="square" />
                    <span className="font-semibold">{c.nom}</span>
                  </div>
                </Td>
                <Td muted>
                  {c.email || c.telephone ? (
                    <div className="flex flex-col">
                      {c.email && <span>{c.email}</span>}
                      {c.telephone && <span className="font-mono text-caption">{c.telephone}</span>}
                    </div>
                  ) : (
                    t('invoices.clients.noContact')
                  )}
                </Td>
                <Td>
                  <span className="inline-flex items-center gap-2 rounded-full border border-outline-variant px-2.5 py-0.5 text-body-sm">
                    <span className="font-mono text-caption font-semibold uppercase">{c.locale ?? 'fr'}</span>
                    {t(c.locale === 'en' ? 'invoices.clients.lang.en' : 'invoices.clients.lang.fr')}
                  </span>
                </Td>
                <Td numeric>
                  <Button variant="ghost" size="sm" onClick={() => start(c)} aria-label={t('invoices.clients.editLabel', { name: c.nom })}>
                    <Pencil className="h-4 w-4" aria-hidden="true" />
                    {t('invoices.clients.edit')}
                  </Button>
                </Td>
              </Tr>
            ))
          ) : status.loading ? (
            <TableState kind="loading" colSpan={4} title={t('invoices.clients.loading')} />
          ) : (
            <TableState
              kind="empty"
              colSpan={4}
              title={clients.length === 0 ? t('invoices.clients.empty') : t('invoices.clients.noMatch', { query })}
              message={clients.length === 0 ? t('invoices.clients.emptyHint') : undefined}
            />
          )}
        </TBody>
      </Table>
      {clients.length > 0 && (
        <p className="m-0 text-body-sm text-on-surface-variant">{t('invoices.clients.count', { count: shown.length })}</p>
      )}

      <Dialog
        open={open}
        onClose={() => { if (!saving) setOpen(false); }}
        title={t(editing ? 'invoices.clients.form.editTitle' : 'invoices.clients.form.addTitle')}
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)} disabled={saving}>
              {t('invoices.clients.form.cancel')}
            </Button>
            <Button type="submit" form="client-form" loading={saving}>
              {t(editing ? 'invoices.clients.form.save' : 'invoices.clients.form.create')}
            </Button>
          </>
        }
      >
        <form id="client-form" onSubmit={submit} className="flex flex-col gap-4" noValidate>
          {error && <FormAlert>{error}</FormAlert>}
          <Field label={t('invoices.clients.form.name')}>
            {({ id }) => <Input id={id} required maxLength={150} value={form.nom} onChange={set('nom')} autoComplete="organization" />}
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label={t('invoices.clients.form.email')}>
              {({ id }) => <Input id={id} type="email" maxLength={100} value={form.email} onChange={set('email')} autoComplete="email" />}
            </Field>
            <Field label={t('invoices.clients.form.phone')}>
              {({ id }) => <Input id={id} type="tel" maxLength={30} value={form.telephone} onChange={set('telephone')} autoComplete="tel" />}
            </Field>
          </div>
          <Field label={t('invoices.clients.form.address')} hint={t('invoices.clients.form.addressHint')}>
            {({ id, describedBy }) => (
              <Textarea id={id} rows={3} maxLength={500} value={form.adresse} onChange={set('adresse')} aria-describedby={describedBy} />
            )}
          </Field>
          <Field label={t('invoices.clients.form.language')} hint={t('invoices.clients.form.languageHint')}>
            {({ id, describedBy }) => (
              <Select id={id} value={form.locale} onChange={set('locale')} aria-describedby={describedBy}>
                <option value="fr">{t('invoices.clients.lang.fr')}</option>
                <option value="en">{t('invoices.clients.lang.en')}</option>
              </Select>
            )}
          </Field>
        </form>
      </Dialog>
    </div>
  );
}
