import React, { useState } from 'react';
import Wordmark from './ui/Wordmark';
import {
  Mail, Phone, MapPin, Clock, Search, Send, HelpCircle,
  CheckCircle2, ChevronDown, ChevronUp, AlertCircle,
  Cloud, ShieldCheck, Code2, ArrowRight, ArrowLeft
} from 'lucide-react';

interface HomepageProps {
  /** Opens the app for a signed-in user, the login form for a visitor. */
  onDashboardClick: () => void;
}

type Page = 'home' | 'services' | 'about' | 'contact';

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

const services = [
  {
    icon: Cloud,
    title: 'Cloud Infrastructure',
    text: 'Scalable and secure cloud architecture designed for high availability and enterprise performance.'
  },
  {
    icon: ShieldCheck,
    title: 'Cybersecurity',
    text: 'Comprehensive threat protection and compliance management to safeguard your critical data assets.'
  },
  {
    icon: Code2,
    title: 'Custom Software',
    text: 'Bespoke application development tailored to streamline your unique operational workflows.'
  }
];

const TAGLINE = 'Digital Intelligence, Expertly Engineered';

// Shared class strings. One lime call-to-action per section; everything else
// is ink, paper or hairline.
const LIME_CTA =
  'inline-flex items-center justify-center gap-2 bg-lime text-ink px-6 py-3 rounded-lg font-semibold text-sm hover:brightness-95 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lime';
const INK_BUTTON =
  'inline-flex items-center justify-center gap-2 bg-ink text-paper px-5 py-2.5 rounded-lg font-semibold text-sm hover:bg-ink/90 transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink';
const FIELD =
  'w-full px-3 py-2.5 bg-white border border-hairline rounded-lg text-sm text-ink placeholder:text-ink-muted outline-none focus:border-ink focus:ring-1 focus:ring-ink transition';
const EYEBROW = 'font-mono text-xs font-medium uppercase tracking-[0.18em]';

export default function Homepage({ onDashboardClick }: HomepageProps) {
  const [currentPage, setCurrentPage] = useState<Page>('home');

  // Contact form state
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('Security audit / Penetration testing');
  const [message, setMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [success, setSuccess] = useState(false);

  // FAQ state
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedFaqIdx, setExpandedFaqIdx] = useState<number | null>(null);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleNavClick = (page: Page) => {
    if (page === 'home') {
      setCurrentPage('home');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (page === 'services') {
      setCurrentPage('home');
      setTimeout(() => scrollToSection('services'), 100);
    } else if (page === 'about') {
      setCurrentPage('home');
      setTimeout(() => scrollToSection('about'), 100);
    } else if (page === 'contact') {
      setCurrentPage('contact');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleContactSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
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
    // Simulate successful submission
    setSuccess(true);
    setName('');
    setEmail('');
    setMessage('');
    setSubject('Security audit / Penetration testing');
    setTimeout(() => setSuccess(false), 5000);
  };

  const filteredFaqs = faqData.filter(
    (faq) =>
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleFaq = (idx: number) => {
    setExpandedFaqIdx(expandedFaqIdx === idx ? null : idx);
  };

  const navLink = (page: Page, label: string) => (
    <button
      onClick={() => handleNavClick(page)}
      className={`text-sm transition hover:text-ink ${
        currentPage === page ? 'text-ink font-semibold' : 'text-ink-muted font-medium'
      }`}
    >
      {label}
    </button>
  );

  const header = (
    <header className="sticky top-0 z-20 bg-paper/90 backdrop-blur border-b border-hairline">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <button onClick={() => handleNavClick('home')} aria-label="DI Xpertia home" className="cursor-pointer">
          <Wordmark />
        </button>
        <nav className="hidden md:flex items-center gap-8">
          {navLink('home', 'Home')}
          {navLink('services', 'Services')}
          {navLink('about', 'About')}
          {navLink('contact', 'Contact')}
        </nav>
        <button onClick={onDashboardClick} className={INK_BUTTON}>
          Go to Dashboard
        </button>
      </div>
    </header>
  );

  const footerLink = (label: string, onClick?: () => void) => (
    <li>
      <button onClick={onClick} className="text-sm text-ink-muted hover:text-ink transition">
        {label}
      </button>
    </li>
  );

  const footer = (
    <footer className="bg-paper border-t border-hairline py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-8">
        <div>
          <Wordmark />
          <p className={`${EYEBROW} mt-4 text-ink-muted`}>{TAGLINE}</p>
          <p className="mt-4 text-xs text-ink-muted">
            © {new Date().getFullYear()} DI Xpertia. All rights reserved.
          </p>
        </div>
        <div>
          <h4 className={`${EYEBROW} text-ink`}>Company</h4>
          <ul className="mt-3 space-y-2">
            {footerLink('About Us', () => handleNavClick('about'))}
            {footerLink('Leadership')}
            {footerLink('Careers')}
          </ul>
        </div>
        <div>
          <h4 className={`${EYEBROW} text-ink`}>Links</h4>
          <ul className="mt-3 space-y-2">
            {footerLink('Services', () => handleNavClick('services'))}
            {footerLink('Case Studies')}
            {footerLink('Go to Dashboard', onDashboardClick)}
          </ul>
        </div>
        <div>
          <h4 className={`${EYEBROW} text-ink`}>Contact</h4>
          <ul className="mt-3 space-y-2">
            {footerLink('Support', () => handleNavClick('contact'))}
            {footerLink('Sales', () => handleNavClick('contact'))}
          </ul>
        </div>
      </div>
    </footer>
  );

  // ---------- Contact Page ----------
  if (currentPage === 'contact') {
    const contactItems = [
      {
        icon: Phone,
        title: 'Emergency Assistance (SLA)',
        value: '+33 (0) 1 45 88 90 22',
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
        value: 'DI Xpertia SAS · Tunis, Tunisie'
      },
      {
        icon: Clock,
        title: 'On-Call Office Uptime',
        value: 'Monday – Friday: 8:00 AM – 7:00 PM',
        note: 'Active network crisis team 24/7/365'
      }
    ];

    return (
      <div className="min-h-screen bg-paper text-ink font-sans">
        {header}

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <button
            onClick={() => handleNavClick('home')}
            className="inline-flex items-center gap-2 text-sm text-ink-muted hover:text-ink transition mb-10"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </button>

          <div className="max-w-2xl mb-12">
            <p className={`${EYEBROW} text-lime-deep`}>Contact</p>
            <h1 className="mt-3 text-3xl md:text-4xl font-bold tracking-[-0.02em]">Contact our experts</h1>
            <p className="mt-4 text-base text-ink-muted leading-relaxed">
              Whether you want a full system audit or to initiate a migration, our on-call architects
              are ready to respond within 4 hours.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Contact details */}
            <div className="lg:col-span-5">
              <h2 className="text-base font-semibold pb-3 border-b border-hairline">Our contact details</h2>
              <ul className="divide-y divide-hairline">
                {contactItems.map(({ icon: Icon, title, value, note }) => (
                  <li key={title} className="flex gap-4 items-start py-5">
                    <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-ink" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold">{title}</h3>
                      <p className="mt-1 font-mono text-sm text-ink">{value}</p>
                      {note && <p className="mt-0.5 text-xs text-ink-muted">{note}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Contact form */}
            <div className="lg:col-span-7 bg-white rounded-2xl border border-hairline p-6 md:p-8">
              <div className="flex items-center justify-between gap-4 pb-4 border-b border-hairline mb-6">
                <h2 className="text-base font-semibold">Inquiry registration form</h2>
                <span className="font-mono text-xs font-medium bg-surface-container text-ink-muted px-2 py-0.5 rounded">
                  REPLY SLA: 4h
                </span>
              </div>

              <form onSubmit={handleContactSubmit} className="flex flex-col gap-5">
                {success && (
                  <div role="status" className="bg-surface-container-low border border-hairline rounded-lg p-4 flex gap-3">
                    <CheckCircle2 className="w-5 h-5 text-ink shrink-0 mt-0.5" />
                    <div>
                      <span className="block text-sm font-semibold">Message received successfully!</span>
                      <p className="text-xs text-ink-muted mt-0.5">
                        A unique incident token has been generated. Our operations center has received it in real time.
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
                    <span className="text-xs font-semibold text-ink-muted">Full Name *</span>
                    <input
                      type="text"
                      placeholder="e.g. Alexandre Dubois"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className={FIELD}
                    />
                  </label>
                  <label className="flex flex-col gap-1.5">
                    <span className="text-xs font-semibold text-ink-muted">Email Address *</span>
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
                  <span className="text-xs font-semibold text-ink-muted">Consultation Topic *</span>
                  <select value={subject} onChange={(e) => setSubject(e.target.value)} className={FIELD}>
                    <option value="Security audit / Penetration testing">Security audit / Penetration testing</option>
                    <option value="Hybrid Cloud Migration">Hybrid Cloud Migration Planning</option>
                    <option value="Custom Development">Custom API / CRM Development</option>
                    <option value="24/7 Support Subscription">24/7 SLA Support Subscription</option>
                    <option value="Other">Other Technology Request</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-ink-muted">Message / Technical Context *</span>
                  <textarea
                    rows={5}
                    placeholder="Briefly describe your company's existing infrastructure, performance goals, or specific regulatory requirements..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className={`${FIELD} resize-none`}
                  />
                </label>

                <button type="submit" className={`${LIME_CTA} self-start`}>
                  <Send className="w-4 h-4" />
                  Submit to Technical Team
                </button>
              </form>
            </div>
          </div>

          {/* FAQ */}
          <section className="mt-20 border-t border-hairline pt-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
              <div className="flex items-start gap-3">
                <HelpCircle className="w-5 h-5 text-ink mt-1" />
                <div>
                  <h2 className="text-xl font-bold tracking-[-0.02em]">Frequently asked questions</h2>
                  <p className="text-sm text-ink-muted mt-1">Search and filter our official answers instantly</p>
                </div>
              </div>
              <div className="relative w-full md:w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
                <input
                  type="text"
                  placeholder="Search (e.g. SLA, security)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`${FIELD} pl-9`}
                />
              </div>
            </div>

            <div className="bg-white border border-hairline rounded-2xl divide-y divide-hairline">
              {filteredFaqs.length > 0 ? (
                filteredFaqs.map((faq, idx) => {
                  const isExpanded = expandedFaqIdx === idx;
                  return (
                    <div key={idx}>
                      <button
                        onClick={() => toggleFaq(idx)}
                        aria-expanded={isExpanded}
                        className="w-full px-5 py-4 flex justify-between items-center gap-4 text-left hover:bg-surface-container-low transition-colors"
                      >
                        <span className="text-sm font-semibold">{faq.question}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-ink-muted shrink-0" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-ink-muted shrink-0" />
                        )}
                      </button>
                      {isExpanded && (
                        <div className="px-5 pb-5 text-sm text-ink-muted leading-relaxed">{faq.answer}</div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8 text-sm text-ink-muted">
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
    <div className="min-h-screen bg-paper text-ink font-sans">
      {header}

      {/* Hero: ink, as on the business card - offset tonal discs and the mark. */}
      <section className="relative overflow-hidden bg-ink text-paper">
        <div aria-hidden="true" className="absolute -right-40 -top-40 w-[36rem] h-[36rem] rounded-full bg-paper/[0.04]"></div>
        <div aria-hidden="true" className="absolute -right-10 top-48 w-[26rem] h-[26rem] rounded-full bg-paper/[0.03]"></div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-28 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <p className={`${EYEBROW} text-paper/60`}>{TAGLINE}</p>
            <h1 className="mt-6 text-4xl sm:text-5xl md:text-6xl font-bold tracking-[-0.02em] leading-[1.05]">
              Digital solutions built around you.
            </h1>
            <p className="mt-6 text-base md:text-lg text-paper/70 max-w-xl leading-relaxed">
              We deliver enterprise-grade IT solutions tailored to your unique operational needs,
              ensuring professional, reliable, and modern technical precision.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <button onClick={() => handleNavClick('contact')} className={LIME_CTA}>
                Contact Us <ArrowRight className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleNavClick('services')}
                className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-semibold text-sm border border-paper/25 text-paper hover:bg-paper/10 transition"
              >
                Our Services
              </button>
            </div>
          </div>
          <div className="hidden lg:flex lg:col-span-5 justify-center">
            <img src="/brand/mark-light.svg" alt="" className="w-64 h-64" />
          </div>
        </div>
      </section>

      {/* Services */}
      <section id="services" className="py-20 scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className={`${EYEBROW} text-lime-deep`}>01 — Services</p>
          <h2 className="mt-3 text-3xl font-bold tracking-[-0.02em]">What we do</h2>
          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
            {services.map(({ icon: Icon, title, text }) => (
              <div key={title} className="p-6 rounded-2xl border border-hairline bg-white flex flex-col">
                <div className="w-11 h-11 rounded-lg bg-surface-container flex items-center justify-center">
                  <Icon className="w-5 h-5 text-ink" />
                </div>
                <h3 className="mt-5 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-ink-muted leading-relaxed flex-1">{text}</p>
                <button
                  onClick={() => handleNavClick('contact')}
                  className="mt-6 inline-flex items-center gap-1.5 self-start text-sm font-semibold text-lime-deep hover:text-ink transition"
                >
                  Learn more <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trusted */}
      <section className="py-12 border-y border-hairline">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className={`${EYEBROW} text-ink-muted`}>Trusted by teams who value reliability</p>
          <div className="mt-6 flex flex-wrap justify-center gap-12 font-mono text-lg text-ink/40">
            <span>LOGO1</span>
            <span>LOGO2</span>
            <span>LOGO3</span>
            <span>LOGO4</span>
          </div>
        </div>
      </section>

      {/* About / CTA: ink again, so the page closes the way it opens. */}
      <section id="about" className="bg-ink text-paper py-20 scroll-mt-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className={`${EYEBROW} text-paper/60`}>02 — About</p>
          <h2 className="mt-4 text-3xl md:text-4xl font-bold tracking-[-0.02em]">
            Ready to transform your IT infrastructure?
          </h2>
          <p className="mt-4 text-base md:text-lg text-paper/70">
            Partner with DI Xpertia to bring modern, reliable technology to your organization.
          </p>
          <button onClick={() => handleNavClick('contact')} className={`${LIME_CTA} mt-10`}>
            Get Started Today <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {footer}
    </div>
  );
}
