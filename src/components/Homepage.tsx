import React, { useState } from 'react';
import HomeHeader, { type HomeTarget } from './home/HomeHeader';
import Hero from './home/Hero';
import HowWeWorkConsole from './home/HowWeWorkConsole';
import Services from './home/Services';
import Engagement from './home/Engagement';
import { ApiError, contact } from '../api';
import AboutCta from './home/AboutCta';
import HomeFooter from './home/HomeFooter';
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

// FAQ data (same as in ContactView, but translated to English)
const faqData = [
  {
    question: 'What types of cloud services do you offer?',
    answer: 'We provide IaaS, PaaS, and SaaS solutions with a multi-cloud architecture (AWS, Azure, GCP) for optimal scalability.'
  },
  {
    question: 'How do you ensure the security of our data?',
    answer: 'We apply ISO 27001 standards, regular audits, and advanced encryption protocols to protect your data.'
  },
  {
    question: 'What is your average support response time?',
    answer: 'Our technical support responds within 4 hours for standard requests, and immediately for critical incidents (24/7 SLA).'
  },
  {
    question: 'Can we migrate an existing infrastructure without service interruption?',
    answer: 'Yes, we plan phased migrations with failover testing to ensure business continuity.'
  },
  {
    question: 'How does your service pricing estimation work?',
    answer: 'We conduct a preliminary audit of your needs, then provide a detailed quote with no obligation.'
  }
];

// Shared class strings for the contact page. They use the homepage roles, so
// the page follows the light/dark theme with the rest of the site (#165).
const LIME_CTA =
  'inline-flex items-center justify-center gap-2 bg-lime text-ink px-6 py-3 rounded-lg font-semibold text-sm hover:brightness-95 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime';
const FIELD =
  'w-full px-3 py-2.5 bg-home-bg border border-home-fg/14 rounded-lg text-sm text-home-fg placeholder:text-home-fg/50 outline-none focus:border-home-fg focus:ring-1 focus:ring-home-fg transition';
const EYEBROW = 'font-mono text-xs font-medium uppercase tracking-[0.18em]';

export default function Homepage({ onDashboardClick }: HomepageProps) {
  const [currentPage, setCurrentPage] = useState<Page>('home');

  // Contact form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('security_audit');
  const [message, setMessage] = useState('');
  // The honeypot (#98): hidden from people, so only a bot fills it in.
  const [website, setWebsite] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
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
    setErrorMsg('');
    setSuccess(false);
    if (!name.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }
    if (message.trim().length < 10) {
      setErrorMsg('Your message must be at least 10 characters.');
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
          ? 'We received many messages in the last hour. Please try again later, or call us on +216 28 814 729.'
          : err instanceof ApiError && err.status === 422
            ? 'Please check the fields: a valid e-mail, and a message of 10 to 5,000 characters.'
            : 'Your message could not be sent. Please try again, or call us on +216 28 814 729.',
      );
    } finally {
      setSending(false);
    }
  };

  const filteredFaqs = faqData.filter(
    (faq) =>
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleFaq = (idx: number) => {
    setExpandedFaqIdx(expandedFaqIdx === idx ? null : idx);
  };

  const header = (
    <HomeHeader
      current={currentPage === 'contact' ? 'contact' : 'home'}
      onNavigate={handleNavClick}
      onDashboardClick={onDashboardClick}
    />
  );

  const footer = <HomeFooter onNavigate={handleNavClick} onDashboardClick={onDashboardClick} />;

  // ---------- Contact Page ----------
  if (currentPage === 'contact') {
    const contactItems = [
      {
        icon: Phone,
        title: 'Emergency Assistance (SLA)',
        value: '+216 28 814 729',
        note: '24/7 emergency line for subscribed clients'
      },
      {
        icon: Mail,
        title: 'Business Integration Inquiries',
        value: 'contact@dixpertia.com',
        note: 'Guaranteed response within 4 business hours'
      },
      {
        icon: MapPin,
        title: 'Technical Headquarters',
        value: 'DI Xpertia SUARL · Rue de Pasteur, Dar Chaabane El Fehri, 8011 Nabeul, Tunisia'
      },
      {
        icon: Clock,
        title: 'On-Call Office Uptime',
        value: 'Monday – Friday: 8:00 AM – 7:00 PM',
        note: 'Active network crisis team 24/7/365'
      }
    ];

    return (
      <div className="home-page min-h-screen bg-home-bg text-home-fg font-sans">
        {header}

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <button
            onClick={() => handleNavClick('home')}
            className="inline-flex items-center gap-2 text-sm text-home-fg/62 hover:text-home-fg transition mb-10"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </button>

          <div className="max-w-2xl mb-12">
            <p className={`${EYEBROW} text-home-accent-text`}>Contact</p>
            <h1 className="mt-3 text-3xl md:text-4xl font-bold tracking-[-0.02em]">Contact our experts</h1>
            <p className="mt-4 text-base text-home-fg/62 leading-relaxed">
              Whether you want a full system audit or to initiate a migration, our on-call architects
              are ready to respond within 4 hours.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Contact details */}
            <div className="lg:col-span-5">
              <h2 className="text-base font-semibold pb-3 border-b border-home-fg/14">Our contact details</h2>
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
                <h2 className="text-base font-semibold">Inquiry registration form</h2>
              </div>

              <form onSubmit={handleContactSubmit} className="relative flex flex-col gap-5" noValidate>
                {success && (
                  <div role="status" className="bg-home-fg/3 border border-home-fg/14 rounded-lg p-4 flex gap-3">
                    <CheckCircle2 className="w-5 h-5 text-home-fg shrink-0 mt-0.5" />
                    <div>
                      <span className="block text-sm font-semibold">Thank you, your message has been sent.</span>
                      <p className="text-xs text-home-fg/62 mt-0.5">
                        Our team has received it and will get back to you by e-mail.
                      </p>
                    </div>
                  </div>
                )}

                {errorMsg && (
                  <div role="alert" className="bg-error-container border border-error/20 rounded-lg p-3 flex gap-2 items-center">
                    <AlertCircle className="w-4 h-4 text-error shrink-0" />
                    <span className="text-sm font-medium text-on-error-container">{errorMsg}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-home-fg/62">Full Name *</span>
                    <input
                      type="text"
                      placeholder="e.g. Alexandre Dubois"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className={FIELD}
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-home-fg/62">Email Address *</span>
                    <input
                      type="email"
                      placeholder="e.g. a.dubois@innovate.fr"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className={FIELD}
                    />
                  </label>
                </div>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-home-fg/62">Consultation Topic *</span>
                  <select value={subject} onChange={(e) => setSubject(e.target.value)} className={FIELD}>
                    <option value="security_audit">Security audit / Penetration testing</option>
                    <option value="cloud_migration">Hybrid Cloud Migration Planning</option>
                    <option value="custom_development">Custom API / CRM Development</option>
                    <option value="support_subscription">Support Subscription</option>
                    <option value="other">Other Technology Request</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-home-fg/62">Message / Technical Context *</span>
                  <textarea
                    rows={5}
                    placeholder="Briefly describe your company's existing infrastructure, performance goals, or specific regulatory requirements..."
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
                  {sending ? 'Sending...' : 'Submit to Technical Team'}
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
                  <h2 className="text-xl font-bold tracking-[-0.02em]">Frequently asked questions</h2>
                  <p className="text-sm text-home-fg/62 mt-1">Search and filter our official answers instantly</p>
                </div>
              </div>
              <div className="relative w-full md:w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-home-fg/62" />
                <input
                  type="text"
                  placeholder="Search (e.g. SLA, security)..."
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
                  No results for "{searchQuery}". Please broaden your search.
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

      <main>
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
