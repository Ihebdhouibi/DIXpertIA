import React, { useState } from 'react';
import { User, Mail, Shield, Bell, Globe, Moon, Sun, Monitor, LogOut, Save, Key } from 'lucide-react';
import { User as UserType } from '../types';
import { ThemePreference, setThemePreference, useThemePreference } from '../theme';
import Button from './ui/Button';
import { Field, Input, Select } from './ui/Field';
import { chooseLocale, useLocale, useT, type MessageKey } from '../i18n';
import { ROLE_LABEL } from '../navigation';

const THEME_OPTIONS: { value: ThemePreference; label: MessageKey; icon: typeof Sun }[] = [
  { value: 'system', label: 'common.settings.theme.system', icon: Monitor },
  { value: 'light', label: 'common.settings.theme.light', icon: Sun },
  { value: 'dark', label: 'common.settings.theme.dark', icon: Moon },
];

interface SettingsViewProps {
  user: UserType;
  onLogout: () => void;
}

export default function SettingsView({ user, onLogout }: SettingsViewProps) {
  const t = useT();
  const theme = useThemePreference();

  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  // The same choice as the FR / EN toggle; App saves it on the account (#135).
  const locale = useLocale();

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">{t('common.settings.title')}</h1>
        <p className="text-body-lg text-on-surface-variant mt-1">
          {t('common.settings.subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left sidebar (navigation) – optional, we skip for simplicity */}

        {/* Main content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Profile Card */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              {t('common.settings.profile')}
            </h2>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-primary text-on-primary flex items-center justify-center text-2xl font-bold">
                {user.firstName[0]}{user.lastName[0]}
              </div>
              <div>
                <p className="text-body-lg font-bold text-on-surface">{user.firstName} {user.lastName}</p>
                <p className="text-body-sm text-on-surface-variant">{user.email}</p>
                <p className="text-caption font-semibold text-primary uppercase">{t(ROLE_LABEL[user.role])}</p>
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              {t('common.settings.appearance')}
            </h2>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p id="theme-label" className="text-body-sm font-semibold text-on-surface">{t('common.settings.theme')}</p>
                <p className="text-caption text-on-surface-variant">
                  {t('common.settings.themeHint')}
                </p>
              </div>
              <div
                role="radiogroup"
                aria-labelledby="theme-label"
                className="inline-flex p-1 rounded-lg bg-surface-container border border-outline-variant"
              >
                {THEME_OPTIONS.map(({ value, label, icon: Icon }) => {
                  const selected = theme === value;
                  return (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setThemePreference(value)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-body-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-primary ${
                        selected
                          ? 'bg-surface-container-lowest text-on-surface shadow-sm'
                          : 'text-on-surface-variant hover:text-on-surface'
                      }`}
                    >
                      <Icon className="w-4 h-4" aria-hidden="true" />
                      {t(label)}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary" />
              {t('common.settings.notificationPreferences')}
            </h2>
            <div className="space-y-3">
              <label className="flex items-center justify-between gap-4 cursor-pointer">
                <span className="text-body-sm font-medium text-on-surface">{t('common.settings.emailNotifications')}</span>
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={() => setEmailNotifications(!emailNotifications)}
                  className="w-4 h-4 accent-primary cursor-pointer"
                />
              </label>
              <label className="flex items-center justify-between gap-4 cursor-pointer">
                <span className="text-body-sm font-medium text-on-surface">{t('common.settings.pushNotifications')}</span>
                <input
                  type="checkbox"
                  checked={pushNotifications}
                  onChange={() => setPushNotifications(!pushNotifications)}
                  className="w-4 h-4 accent-primary cursor-pointer"
                />
              </label>
            </div>
          </div>

          {/* Language */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5 text-primary" />
              {t('common.language')}
            </h2>
            <Field label={t('common.settings.interfaceLanguage')} className="md:w-56">
              {({ id }) => (
                <Select id={id} value={locale} onChange={(e) => chooseLocale(e.target.value === 'en' ? 'en' : 'fr')}>
                  <option value="fr" lang="fr">Français</option>
                  <option value="en" lang="en">English</option>
                </Select>
              )}
            </Field>
          </div>

          {/* Change Password */}
          <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Key className="w-5 h-5 text-primary" />
              {t('common.settings.changePassword')}
            </h2>
            <form className="flex flex-col gap-4 md:max-w-md" onSubmit={(e) => e.preventDefault()}>
              {/* Placeholders were the only labels; each field now has a real one. */}
              <Field label={t('common.settings.currentPassword')}>
                {({ id }) => <Input id={id} type="password" autoComplete="current-password" />}
              </Field>
              <Field label={t('common.settings.newPassword')}>
                {({ id }) => <Input id={id} type="password" autoComplete="new-password" />}
              </Field>
              <Field label={t('common.settings.confirmNewPassword')}>
                {({ id }) => <Input id={id} type="password" autoComplete="new-password" />}
              </Field>
              <Button type="submit" className="self-start">
                <Save className="w-4 h-4" aria-hidden="true" />
                {t('common.settings.updatePassword')}
              </Button>
            </form>
          </div>

          {/* Danger Zone */}
          <div className="bg-surface-container-lowest rounded-xl border border-error/20 shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-error mb-4">{t('common.settings.dangerZone')}</h2>
            <Button variant="danger" onClick={onLogout}>
              <LogOut className="w-4 h-4" aria-hidden="true" />
              {t('common.signOut')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
