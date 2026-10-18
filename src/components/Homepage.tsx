import React, { useState } from 'react';
import HomeHeader, { type HomeTarget } from './home/HomeHeader';
import Hero from './home/Hero';
import HowWeWorkConsole from './home/HowWeWorkConsole';
import Services from './home/Services';
import Engagement from './home/Engagement';
import { ApiError, contact } from '../api';
import AboutCta from './home/AboutCta';
import HomeFooter from './home/HomeFooter';
import SkipLink from './ui/SkipLink';
import { useT, type MessageKey } from '../i18n';
import {
  Mail, Phone, MapPin, Clock, Search, Send, HelpCircle,
  CheckCircle2, ChevronDown, ChevronUp, AlertCircle, ArrowLeft
} from 'lucide-react';

interface HomepageProps {
  /** Opens the app for a signed-in user, the login form for a visitor. */
  onDashboardClick: () => void;
}

type Page = HomeTarget;

/** Smooth scrolling, unless the visitor asked for less motion. */
const scrollBehavior = (): ScrollBehavior =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

// FAQ entries (question and answer keys). Worded without guarantees the
// company has not committed to: no response times, no 24/7 line, no
// certification (#98).
const FAQ: { question: MessageKey; answer: MessageKey }[] = [
  { question: 'home.faq.cloud.q', answer: 'home.faq.cloud.a' },
  { question: 'home.faq.security.q', answer: 'home.faq.security.a' },
  { question: 'home.faq.response.q', answer: 'home.faq.response.a' },
  { question: 'home.faq.migration.q', answer: 'home.faq.migration.a' },
  { question: 'home.faq.pricing.q', answer: 'home.faq.pricing.a' },
];

/** The topics the API accepts; only their labels are translated. */
const TOPICS = ['security_audit', 'cloud_migration', 'custom_development', 'support_subscription', 'other'] as const;

const PHONE = '+216 28 814 729';

// Shared class strings for the contact page. They use the homepage roles, so
// the page follows the light/dark theme with the rest of the site (#165).
const LIME_CTA =
  'inline-flex items-center justify-center gap-2 bg-lime text-ink px-6 py-3 rounded-lg font-semibold text-sm hover:brightness-95 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime';
const FIELD =
  'w-full px-3 py-2.5 bg-home-bg border border-home-fg/14 rounded-lg text-sm text-home-fg placeholder:text-home-fg/50 outline-none focus:border-home-fg focus:ring-1 focus:ring-home-fg transition';
const EYEBROW = 'font-mono text-xs font-medium uppercase tracking-[0.18em]';

export default function Homepage({ onDashboardClick }: HomepageProps) {
  const t = useT();
  const [currentPage, setCurrentPage] = useState<Page>('home');

  // Contact form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('security_audit');
  const [message, setMessage] = useState('');
  // The honeypot (#98): hidden from people, so only a bot fills it in.
  const [website, setWebsite] = useState('');
  // The error's key, not its text, so it follows a change of language.
  const [errorMsg, setErrorMsg] = useState<MessageKey | null>(null);
  const [success, setSuccess] = useState(false);
  const [sending, setSending] = useState(false);

  // FAQ state
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFaqIdx, setExpandedFaqIdx] = useState<number | null>(null);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: scrollBehavior() });
    }
  };

  const handleNavClick = (page: Page) => {
    if (page === 'home') {
      setCurrentPage('home');
      window.scrollTo({ top: 0, behavior: scrollBehavior() });
    } else if (page === 'services') {
      setCurrentPage('home');
      setTimeout(() => scrollToSection('services'), 100);
    } else if (page === 'about') {
      setCurrentPage('home');
      setTimeout(() => scrollToSection('about'), 100);
    } else if (page === 'contact') {
      setCurrentPage('contact');
      window.scrollTo({ top: 0, behavior: scrollBehavior() });
    }
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccess(false);
    if (!name.trim()) {
      setErrorMsg('home.contact.error.name');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('home.contact.error.email');
      return;
    }
    if (message.trim().length < 10) {
      setErrorMsg('home.contact.error.messageLength');
      return;
    }
    // The enquiry goes to the server (#98), which stores it and tells the
    // team. It used to "simulate" success here while nothing was sent.
    setSending(true);
    try {
      await contact.send({ name: name.trim(), email: email.trim(), topic: subject, message: message.trim(), website });
      setSuccess(true);
      setName('');
      setEmail('');
      setMessage('');
      setSubject('security_audit');
    } catch (err) {
      setErrorMsg(
        err instanceof ApiError && err.status === 429
          ? 'home.contact.error.tooMany'
          : err instanceof ApiError && err.status === 422
            ? 'home.contact.error.invalid'
            : 'home.contact.error.notSent',
      );
    } finally {
      setSending(false);
    }
  };

  // Searched in the language shown, so a French query finds French answers.
  const faqs = FAQ.map(({ question, answer }) => ({ question: t(question), answer: t(answer) }));
  const filteredFaqs = faqs.filter(
    (faq) =>
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleFaq = (idx: number) => {
    setExpandedFaqIdx(expandedFaqIdx === idx ? null : idx);
  };

  const header = (
    <>
    <SkipLink />
    <HomeHeader
      current={currentPage === 'contact' ? 'contact' : 'home'}
      onNavigate={handleNavClick}
      onDashboardClick={onDashboardClick}
    />
    </>
  );

  const footer = <HomeFooter onNavigate={handleNavClick} onDashboardClick={onDashboardClick} />;

  // ---------- Contact Page ----------
  if (currentPage === 'contact') {
    const contactItems = [
      {
        icon: Phone,
        title: t('home.contact.phone'),
        value: PHONE,
        note: t('home.contact.phoneNote')
      },
      {
        icon: Mail,
        title: t('home.contact.business'),
        value: 'contact@dixpertia.com',
        note: t('home.contact.businessNote')
      },
      {
        icon: MapPin,
        title: t('home.contact.headquarters'),
        value: t('home.contact.address')
      },
      {
        icon: Clock,
        title: t('home.contact.hours'),
        value: t('home.contact.hoursValue')
      }
    ];

    return (
      <div className="home-page min-h-screen bg-home-bg text-home-fg font-sans">
        {header}

        <main id="main-content" tabIndex={-1} className="focus:outline-none max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <button
            onClick={() => handleNavClick('home')}
            className="inline-flex items-center gap-2 text-sm text-home-fg/62 hover:text-home-fg transition mb-10"
          >
            <ArrowLeft className="w-4 h-4" /> {t('home.contact.back')}
          </button>

          <div className="max-w-2xl mb-12">
            <p className={`${EYEBROW} text-home-accent-text`}>{t('home.contact.eyebrow')}</p>
            <h1 className="mt-3 text-3xl md:text-4xl font-bold tracking-[-0.02em]">{t('home.contact.title')}</h1>
            <p className="mt-4 text-base text-home-fg/62 leading-relaxed">
              {t('home.contact.intro')}
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Contact details */}
            <div className="lg:col-span-5">
              <h2 className="text-base font-semibold pb-3 border-b border-home-fg/14">{t('home.contact.details')}</h2>
              <ul className="divide-y divide-home-fg/14">
                {contactItems.map(({ icon: Icon, title, value, note }) => (
                  <li key={title} className="flex gap-4 items-start py-5">
                    <div className="w-10 h-10 rounded-lg bg-home-fg/5 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-home-fg" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{title}</h3>
                      <p className="mt-1 font-mono text-sm text-home-fg">{value}</p>
                      {note && <p className="mt-0.5 text-xs text-home-fg/62">{note}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Contact form */}
            <div className="lg:col-span-7 bg-home-surface rounded-2xl border border-home-fg/14 p-6 md:p-8">
              <div className="pb-4 border-b border-home-fg/14 mb-6">
                <h2 className="text-base font-semibold">{t('home.contact.form.title')}</h2>
              </div>

              <form onSubmit={handleContactSubmit} className="relative flex flex-col gap-5" noValidate>
                {success && (
                  <div role="status" className="bg-home-fg/3 border border-home-fg/14 rounded-lg p-4 flex gap-3">
                    <CheckCircle2 className="w-5 h-5 text-home-fg shrink-0 mt-0.5" />
                    <div>
                      <span className="block text-sm font-semibold">{t('home.contact.form.sent')}</span>
                      <p className="text-xs text-home-fg/62 mt-0.5">
                        {t('home.contact.form.sentHint')}
                      </p>
                    </div>
                  </div>
                )}

                {errorMsg && (
                  <div role="alert" className="bg-error-container border border-error/20 rounded-lg p-3 flex gap-2 items-center">
                    <AlertCircle className="w-4 h-4 text-error shrink-0" />
                    <span className="text-sm font-medium text-on-error-container">{t(errorMsg, { phone: PHONE })}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-home-fg/62">{t('home.contact.form.name')}</span>
                    <input
                      type="text"
                      placeholder={t('home.contact.form.namePlaceholder')}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className={FIELD}
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-home-fg/62">{t('home.contact.form.email')}</span>
                    <input
                      type="email"
                      placeholder={t('home.contact.form.emailPlaceholder')}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className={FIELD}
                    />
                  </label>
                </div>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-home-fg/62">{t('home.contact.form.topic')}</span>
                  <select value={subject} onChange={(e) => setSubject(e.target.value)} className={FIELD}>
                    {TOPICS.map((topic) => (
                      <option key={topic} value={topic}>{t(`home.contact.form.topic.${topic}`)}</option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-home-fg/62">{t('home.contact.form.message')}</span>
                  <textarea
                    rows={5}
                    placeholder={t('home.contact.form.messagePlaceholder')}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className={`${FIELD} resize-none`}
                  />
                </label>

                {/* Honeypot (#98): off-screen and out of the tab order, so people
                    never see or reach it; bots that fill every field do. */}
                <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
                  <label>
                    Website
                    <input type="text" tabIndex={-1} autoComplete="off" value={website} onChange={(e) => setWebsite(e.target.value)} />
                  </label>
                </div>

                <button type="submit" disabled={sending} className={`${LIME_CTA} self-start disabled:cursor-wait disabled:opacity-70`}>
                  <Send className="w-4 h-4" aria-hidden="true" />
                  {sending ? t('home.contact.form.sending') : t('home.contact.form.submit')}
                </button>
              </form>
            </div>
          </div>

          {/* FAQ */}
          <section className="mt-20 border-t border-home-fg/14 pt-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
              <div className="flex items-start gap-3">
                <HelpCircle className="w-5 h-5 text-home-fg mt-1" />
                <div>
                  <h2 className="text-xl font-bold tracking-[-0.02em]">{t('home.faq.title')}</h2>
                  <p className="text-sm text-home-fg/62 mt-1">{t('home.faq.subtitle')}</p>
                </div>
              </div>
              <div className="relative w-full md:w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-home-fg/62" />
                <input
                  type="text"
                  placeholder={t('home.faq.search')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`${FIELD} pl-9`}
                />
              </div>
            </div>

            <div className="bg-home-surface border border-home-fg/14 rounded-2xl divide-y divide-home-fg/14">
              {filteredFaqs.length > 0 ? (
                filteredFaqs.map((faq, idx) => {
                  const isExpanded = expandedFaqIdx === idx;
                  return (
                    <div key={idx}>
                      <button
                        onClick={() => toggleFaq(idx)}
                        aria-expanded={isExpanded}
                        className="w-full px-5 py-4 flex justify-between items-center gap-4 text-left hover:bg-home-fg/3 transition-colors"
                      >
                        <span className="text-sm font-semibold">{faq.question}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-home-fg/62 shrink-0" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-home-fg/62 shrink-0" />
                        )}
                      </button>
                      {isExpanded && (
                        <div className="px-5 pb-5 text-sm text-home-fg/62 leading-relaxed">{faq.answer}</div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8 text-sm text-home-fg/62">
                  {t('home.faq.noResults', { query: searchQuery })}
                </div>
              )}
            </div>
          </section>
        </main>

        {footer}
      </div>
    );
  }

  // ---------- Homepage (default) ----------
  return (
    <div className="home-page min-h-screen bg-home-bg text-home-fg font-sans">
      {header}

      <main id="main-content" tabIndex={-1} className="focus:outline-none">
        <Hero
          onContact={() => handleNavClick('contact')}
          onServices={() => handleNavClick('services')}
          console={<HowWeWorkConsole />}
        />

        <Services onPick={() => handleNavClick('contact')} />
        <Engagement />

        <AboutCta onStart={() => handleNavClick('contact')} />
      </main>

      {footer}
    </div>
  );
}
