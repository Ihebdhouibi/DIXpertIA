import React, { useState } from 'react';
import { User, Mail, Shield, Bell, Globe, Moon, Sun, LogOut, Save, Key } from 'lucide-react';
import { User as UserType } from '../types';

interface SettingsViewProps {
  user: UserType;
  onLogout: () => void;
}

export default function SettingsView({ user, onLogout }: SettingsViewProps) {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('dixpertia_darkmode');
    return saved ? JSON.parse(saved) : false;
  });

  const [emailNotifications, setEmailNotifications] = useState(true);
  const [pushNotifications, setPushNotifications] = useState(true);
  const [language, setLanguage] = useState('en');

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('dixpertia_darkmode', JSON.stringify(newMode));
    // Apply dark mode to document (if you have a dark theme)
    document.documentElement.classList.toggle('dark', newMode);
  };

  return (
    <div className="flex-1 flex flex-col gap-6 animate-fade-in max-w-4xl">
      <div>
        <h1 className="text-h1 font-black text-on-surface tracking-tight md:text-display">Settings</h1>
        <p className="text-body-lg text-on-surface-variant mt-1">
          Manage your profile, preferences, and account settings.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left sidebar (navigation) – optional, we skip for simplicity */}

        {/* Main content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Profile Card */}
          <div className="bg-white rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-primary" />
              Profile
            </h2>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-primary text-white flex items-center justify-center text-2xl font-bold">
                {user.firstName[0]}{user.lastName[0]}
              </div>
              <div>
                <p className="text-body-lg font-bold text-on-surface">{user.firstName} {user.lastName}</p>
                <p className="text-body-sm text-on-surface-variant">{user.email}</p>
                <p className="text-caption font-semibold text-primary uppercase">{user.role}</p>
              </div>
            </div>
          </div>

          {/* Appearance */}
          <div className="bg-white rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              Appearance
            </h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-body-sm font-semibold text-on-surface">Dark Mode</p>
                <p className="text-caption text-on-surface-variant">Toggle dark theme (experimental)</p>
              </div>
              <button
                onClick={toggleDarkMode}
                className={`relative w-12 h-6 rounded-full transition-colors ${darkMode ? 'bg-primary' : 'bg-outline-variant'}`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                    darkMode ? 'translate-x-6' : ''
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-white rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Bell className="w-5 h-5 text-primary" />
              Notification Preferences
            </h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-body-sm font-medium text-on-surface">Email Notifications</span>
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={() => setEmailNotifications(!emailNotifications)}
                  className="w-4 h-4 text-primary rounded border-outline-variant focus:ring-primary"
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-body-sm font-medium text-on-surface">Push Notifications</span>
                <input
                  type="checkbox"
                  checked={pushNotifications}
                  onChange={() => setPushNotifications(!pushNotifications)}
                  className="w-4 h-4 text-primary rounded border-outline-variant focus:ring-primary"
                />
              </div>
            </div>
          </div>

          {/* Language */}
          <div className="bg-white rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Globe className="w-5 h-5 text-primary" />
              Language
            </h2>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full md:w-48 px-3 py-2 border border-outline-variant rounded-lg bg-surface text-body-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </div>

          {/* Change Password */}
          <div className="bg-white rounded-xl border border-outline-variant shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-on-surface mb-4 flex items-center gap-2">
              <Key className="w-5 h-5 text-primary" />
              Change Password
            </h2>
            <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
              <input
                type="password"
                placeholder="Current password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg focus:outline-none focus:ring-1 focus:ring-primary text-body-sm"
              />
              <input
                type="password"
                placeholder="New password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg focus:outline-none focus:ring-1 focus:ring-primary text-body-sm"
              />
              <input
                type="password"
                placeholder="Confirm new password"
                className="w-full px-3 py-2 border border-outline-variant rounded-lg focus:outline-none focus:ring-1 focus:ring-primary text-body-sm"
              />
              <button
                type="submit"
                className="bg-primary text-white px-4 py-2 rounded-lg font-bold hover:bg-primary/95 transition shadow-sm flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                Update Password
              </button>
            </form>
          </div>

          {/* Danger Zone */}
          <div className="bg-white rounded-xl border border-error/20 shadow-sm p-6">
            <h2 className="text-body-lg font-bold text-error mb-4">Danger Zone</h2>
            <button
              onClick={onLogout}
              className="bg-error hover:bg-error/90 text-white px-4 py-2 rounded-lg font-bold transition flex items-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}