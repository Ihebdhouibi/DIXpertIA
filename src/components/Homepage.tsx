import React, { useState } from 'react';
import { 
  Mail, Phone, MapPin, Clock, Search, Send, HelpCircle, 
  CheckCircle2, ChevronDown, ChevronUp, AlertCircle 
} from 'lucide-react';

interface HomepageProps {
  onLoginClick: () => void;
  showDashboardButton?: boolean;
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

export default function Homepage({ onLoginClick, showDashboardButton }: HomepageProps) {
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

  // ---------- Contact Page ----------
  if (currentPage === 'contact') {
    return (
      <div className="min-h-screen bg-white text-on-surface font-sans">
        {/* Header (same as homepage) */}
        <header className="border-b border-outline-variant/30 bg-surface-container-lowest sticky top-0 z-10">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
            <button
              onClick={() => handleNavClick('home')}
              className="text-primary font-black text-2xl tracking-tight hover:opacity-80 transition cursor-pointer"
            >
              DIXpertIA
            </button>
            <nav className="hidden md:flex items-center gap-6 text-body-sm font-medium text-on-surface-variant">
              <button onClick={() => handleNavClick('home')} className="hover:text-primary transition">Home</button>
              <button onClick={() => handleNavClick('services')} className="hover:text-primary transition">Services</button>
              <button onClick={() => handleNavClick('about')} className="hover:text-primary transition">About</button>
              <button onClick={() => handleNavClick('contact')} className="text-primary font-semibold">Contact</button>
            </nav>
            <div className="flex items-center gap-2">
              {showDashboardButton && (
                <button
                  onClick={onLoginClick}
                  className="bg-secondary text-white px-5 py-2 rounded-lg font-semibold hover:bg-secondary/90 transition shadow-sm"
                >
                  Go to Dashboard
                </button>
              )}
              {!showDashboardButton && (
                <button
                  onClick={onLoginClick}
                  className="bg-primary text-white px-5 py-2 rounded-lg font-semibold hover:bg-primary/95 transition shadow-sm"
                >
                  Employee Login
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Contact Page Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Back to Home */}
          <button
            onClick={() => handleNavClick('home')}
            className="inline-flex items-center gap-2 text-body-sm text-outline hover:text-primary transition mb-8"
          >
            ← Back to Home
          </button>

          <div className="text-center max-w-2xl mx-auto mb-12">
            <h1 className="text-3xl font-bold text-[#03224d]">Contact Our Experts</h1>
            <p className="text-sm text-gray-500 mt-3 leading-relaxed">
              Whether you want a full system audit or to initiate a migration, our on‑call architects
              are ready to respond within 4 hours.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Contact Info (left) */}
            <div className="lg:col-span-5 flex flex-col gap-6 text-left">
              <h2 className="font-bold text-base text-[#03224d] pb-2 border-b border-gray-100">Our Contact Details</h2>
              <div className="flex flex-col gap-5">
                <div className="flex gap-4 items-start">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                    <Phone className="w-5 h-5 text-[#03224d]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-gray-900">Emergency Assistance (SLA)</h4>
                    <p className="text-xs font-semibold text-[#0e61a1] mt-1">+33 (0) 1 45 88 90 22</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">24/7 emergency line for subscribed clients</p>
                  </div>
                </div>
                <div className="flex gap-4 items-start border-t border-gray-200/40 pt-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                    <Mail className="w-5 h-5 text-[#03224d]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-gray-900">Business Integration Inquiries</h4>
                    <p className="text-xs font-semibold text-[#0e61a1] mt-1">contact@dixpertia.com</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">Guaranteed response within 4 business hours</p>
                  </div>
                </div>
                <div className="flex gap-4 items-start border-t border-gray-200/40 pt-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                    <MapPin className="w-5 h-5 text-[#03224d]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-gray-900">Technical Headquarters</h4>
                    <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                      DIXpertIA SAS<br />
                      Tunis, Tunisie
                    </p>
                  </div>
                </div>
                <div className="flex gap-4 items-start border-t border-gray-200/40 pt-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
                    <Clock className="w-5 h-5 text-[#03224d]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-xs text-gray-900">On‑Call Office Uptime</h4>
                    <p className="text-xs text-gray-600 mt-1">Monday – Friday: 8:00 AM – 7:00 PM</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">Active network crisis team 24/7/365</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Contact Form (right) */}
            <div className="lg:col-span-7 bg-white rounded-2xl border border-gray-200 p-6 md:p-8 text-left shadow-sm">
              <div className="flex items-center justify-between pb-4 border-b border-gray-100 mb-6">
                <h2 className="font-bold text-base text-[#03224d]">Inquiry Registration Form</h2>
                <span className="font-mono text-[10px] bg-amber-50 text-amber-800 border border-amber-200 px-2 py-0.5 rounded font-bold">
                  REPLY SLA: 4h
                </span>
              </div>

              <form onSubmit={handleContactSubmit} className="flex flex-col gap-4">
                {success && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex gap-3 text-left animate-fade-in">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="block text-xs font-bold text-emerald-800">Message received successfully!</span>
                      <p className="text-[11px] text-emerald-700 mt-0.5">
                        A unique incident token has been generated. Our operations center has received it in real time.
                      </p>
                    </div>
                  </div>
                )}

                {errorMsg && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex gap-2 text-left items-center animate-fade-in">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                    <span className="text-xs font-semibold text-red-800">{errorMsg}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-600">Full Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Alexandre Dubois"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="p-2.5 border border-gray-200 rounded text-xs focus:ring-1 focus:ring-[#03224d] outline-none"
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-gray-600">Email Address *</label>
                    <input
                      type="email"
                      placeholder="e.g. a.dubois@innovate.fr"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="p-2.5 border border-gray-200 rounded text-xs focus:ring-1 focus:ring-[#03224d] outline-none"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-600">Consultation Topic *</label>
                  <select
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="p-2.5 border border-gray-200 rounded text-xs bg-white focus:ring-1 focus:ring-[#03224d] outline-none"
                  >
                    <option value="Security audit / Penetration testing">Security audit / Penetration testing</option>
                    <option value="Hybrid Cloud Migration">Hybrid Cloud Migration Planning</option>
                    <option value="Custom Development">Custom API / CRM Development</option>
                    <option value="24/7 Support Subscription">24/7 SLA Support Subscription</option>
                    <option value="Other">Other Technology Request</option>
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-gray-600">Message / Technical Context *</label>
                  <textarea
                    rows={5}
                    placeholder="Briefly describe your company's existing infrastructure, performance goals, or specific regulatory requirements..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="p-3 border border-gray-200 rounded text-xs focus:ring-1 focus:ring-[#03224d] outline-none resize-none"
                  />
                </div>

                <button
                  type="submit"
                  className="mt-2 bg-[#03224d] hover:bg-[#1f3864] text-white text-xs font-bold py-3 px-5 rounded-lg transition-colors flex items-center justify-center gap-2 self-start cursor-pointer active:scale-95"
                >
                  <Send className="w-3.5 h-3.5" />
                  Submit to Technical Team
                </button>
              </form>
            </div>
          </div>

          {/* FAQ Section */}
          <section className="mt-16 bg-slate-50 rounded-2xl border border-gray-200 p-6 md:p-8 flex flex-col gap-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-gray-200 text-left">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-[#03224d]" />
                <div>
                  <h2 className="font-bold text-base text-[#03224d]">Frequently Asked Questions</h2>
                  <p className="text-[11px] text-gray-400">Search and filter our official answers instantly</p>
                </div>
              </div>
              <div className="relative max-w-sm w-full md:w-64">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search (e.g. SLA, security)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white border border-gray-200 pl-9 pr-3 py-1.5 rounded text-xs outline-none focus:ring-1 focus:ring-[#03224d]"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3">
              {filteredFaqs.length > 0 ? (
                filteredFaqs.map((faq, idx) => {
                  const isExpanded = expandedFaqIdx === idx;
                  return (
                    <div
                      key={idx}
                      className="bg-white border border-gray-200/60 rounded-xl overflow-hidden transition-all text-left"
                    >
                      <button
                        onClick={() => toggleFaq(idx)}
                        className="w-full px-5 py-4 flex justify-between items-center hover:bg-gray-50/50 transition-colors"
                      >
                        <span className="font-semibold text-xs text-[#03224d]">{faq.question}</span>
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </button>
                      {isExpanded && (
                        <div className="px-5 pb-5 pt-1 text-xs text-gray-500 leading-relaxed border-t border-gray-50 animate-fade-in">
                          {faq.answer}
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-gray-400">
                  No results for "{searchQuery}". Please broaden your search.
                </div>
              )}
            </div>
          </section>
        </main>

        {/* Footer (same as homepage) */}
        <footer className="bg-surface-container-lowest border-t border-outline-variant/30 py-12 px-4 mt-12">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="text-primary font-black text-2xl">DIXpertIA</div>
              <p className="mt-2 text-body-sm text-on-surface-variant">
                Enterprise IT Solutions built on a foundation of reliability, security, and precision.
              </p>
              <p className="mt-4 text-caption text-outline">© 2024 DIXpertIA. All rights reserved.</p>
            </div>
            <div>
              <h4 className="font-bold text-body-sm text-on-surface">Company</h4>
              <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
                <li><button onClick={() => handleNavClick('about')} className="hover:text-primary transition">About Us</button></li>
                <li><button className="hover:text-primary transition">Leadership</button></li>
                <li><button className="hover:text-primary transition">Careers</button></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-body-sm text-on-surface">Links</h4>
              <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
                <li><button onClick={() => handleNavClick('services')} className="hover:text-primary transition">Services</button></li>
                <li><button className="hover:text-primary transition">Case Studies</button></li>
                <li><button onClick={onLoginClick} className="hover:text-primary transition">Employee Portal</button></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-body-sm text-on-surface">Contact</h4>
              <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
                <li><button onClick={() => handleNavClick('contact')} className="hover:text-primary transition">Support</button></li>
                <li><button onClick={() => handleNavClick('contact')} className="hover:text-primary transition">Sales</button></li>
              </ul>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  // ---------- Homepage (default) ----------
  return (
    <div className="min-h-screen bg-white text-on-surface font-sans">
      {/* Header */}
      <header className="border-b border-outline-variant/30 bg-surface-container-lowest sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <button
            onClick={() => handleNavClick('home')}
            className="text-primary font-black text-2xl tracking-tight hover:opacity-80 transition cursor-pointer"
          >
            DIXpertIA
          </button>
          <nav className="hidden md:flex items-center gap-6 text-body-sm font-medium text-on-surface-variant">
            <button onClick={() => handleNavClick('home')} className="hover:text-primary transition">Home</button>
            <button onClick={() => handleNavClick('services')} className="hover:text-primary transition">Services</button>
            <button onClick={() => handleNavClick('about')} className="hover:text-primary transition">About</button>
            <button onClick={() => handleNavClick('contact')} className="hover:text-primary transition">Contact</button>
          </nav>
          <div className="flex items-center gap-2">
            {showDashboardButton && (
              <button
                onClick={onLoginClick}
                className="bg-secondary text-white px-5 py-2 rounded-lg font-semibold hover:bg-secondary/90 transition shadow-sm"
              >
                Go to Dashboard
              </button>
            )}
            {!showDashboardButton && (
              <button
                onClick={onLoginClick}
                className="bg-primary text-white px-5 py-2 rounded-lg font-semibold hover:bg-primary/95 transition shadow-sm"
              >
                Employee Login
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-surface-container-low to-white py-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl md:text-display font-black text-on-surface tracking-tight leading-tight">
            Digital solutions built <br className="hidden sm:block" /> around you.
          </h1>
          <p className="mt-4 text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            We deliver enterprise-grade IT solutions tailored to your unique operational needs,
            ensuring professional, reliable, and modern technical precision.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <button
              onClick={() => handleNavClick('services')}
              className="bg-primary text-white px-6 py-3 rounded-lg font-bold text-body-sm hover:bg-primary/95 transition shadow-sm"
            >
              Our Services
            </button>
            <button
              onClick={() => handleNavClick('contact')}
              className="bg-surface-container-lowest border border-outline-variant text-on-surface px-6 py-3 rounded-lg font-bold text-body-sm hover:bg-surface-container-low transition shadow-sm"
            >
              Contact Us
            </button>
          </div>
        </div>
      </section>

      {/* Services */}
      <section id="services" className="py-16 px-4 bg-white scroll-mt-16">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-h2 font-black text-on-surface text-center mb-12">What We Do</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-xl border border-outline-variant/30 shadow-sm hover:shadow-md transition bg-surface-container-lowest">
              <div className="w-12 h-12 rounded-full bg-primary-container text-primary flex items-center justify-center text-2xl mb-4">☁️</div>
              <h3 className="text-body-lg font-bold text-on-surface">Cloud Infrastructure</h3>
              <p className="mt-2 text-body-sm text-on-surface-variant">
                Scalable and secure cloud architecture designed for high availability and enterprise performance.
              </p>
              <button className="mt-4 inline-block text-primary font-semibold text-body-sm hover:underline">
                Learn more →
              </button>
            </div>
            <div className="p-6 rounded-xl border border-outline-variant/30 shadow-sm hover:shadow-md transition bg-surface-container-lowest">
              <div className="w-12 h-12 rounded-full bg-secondary-container text-secondary flex items-center justify-center text-2xl mb-4">🔒</div>
              <h3 className="text-body-lg font-bold text-on-surface">Cybersecurity</h3>
              <p className="mt-2 text-body-sm text-on-surface-variant">
                Comprehensive threat protection and compliance management to safeguard your critical data assets.
              </p>
              <button className="mt-4 inline-block text-primary font-semibold text-body-sm hover:underline">
                Learn more →
              </button>
            </div>
            <div className="p-6 rounded-xl border border-outline-variant/30 shadow-sm hover:shadow-md transition bg-surface-container-lowest">
              <div className="w-12 h-12 rounded-full bg-tertiary-container text-tertiary flex items-center justify-center text-2xl mb-4">⚙️</div>
              <h3 className="text-body-lg font-bold text-on-surface">Custom Software</h3>
              <p className="mt-2 text-body-sm text-on-surface-variant">
                Bespoke application development tailored to streamline your unique operational workflows.
              </p>
              <button className="mt-4 inline-block text-primary font-semibold text-body-sm hover:underline">
                Learn more →
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Trusted */}
      <section className="py-12 px-4 bg-surface-container-low border-y border-outline-variant/30">
        <div className="max-w-7xl mx-auto text-center">
          <p className="text-body-sm font-semibold text-on-surface-variant uppercase tracking-wider">Trusted by teams who value reliability</p>
          <div className="mt-6 flex flex-wrap justify-center gap-12 text-on-surface-variant/60 font-bold text-lg">
            <span>LOGO1</span>
            <span>LOGO2</span>
            <span>LOGO3</span>
            <span>LOGO4</span>
          </div>
        </div>
      </section>

      {/* About / CTA */}
      <section id="about" className="py-16 px-4 bg-primary-container/20 scroll-mt-16">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-h2 font-black text-on-surface">Ready to transform your IT infrastructure?</h2>
          <p className="mt-4 text-body-lg text-on-surface-variant">
            Partner with DIXpertIA to bring modern, reliable technology to your organization.
          </p>
          <button
            onClick={() => handleNavClick('contact')}
            className="mt-8 bg-primary text-white px-8 py-3 rounded-lg font-bold text-body-sm hover:bg-primary/95 transition shadow-sm"
          >
            Get Started Today
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface-container-lowest border-t border-outline-variant/30 py-12 px-4">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="text-primary font-black text-2xl">DIXpertIA</div>
            <p className="mt-2 text-body-sm text-on-surface-variant">
              Enterprise IT Solutions built on a foundation of reliability, security, and precision.
            </p>
            <p className="mt-4 text-caption text-outline">© 2024 DIXpertIA. All rights reserved.</p>
          </div>
          <div>
            <h4 className="font-bold text-body-sm text-on-surface">Company</h4>
            <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
              <li><button onClick={() => handleNavClick('about')} className="hover:text-primary transition">About Us</button></li>
              <li><button className="hover:text-primary transition">Leadership</button></li>
              <li><button className="hover:text-primary transition">Careers</button></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-body-sm text-on-surface">Links</h4>
            <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
              <li><button onClick={() => handleNavClick('services')} className="hover:text-primary transition">Services</button></li>
              <li><button className="hover:text-primary transition">Case Studies</button></li>
              <li><button onClick={onLoginClick} className="hover:text-primary transition">Employee Portal</button></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-body-sm text-on-surface">Contact</h4>
            <ul className="mt-2 space-y-1 text-body-sm text-on-surface-variant">
              <li><button onClick={() => handleNavClick('contact')} className="hover:text-primary transition">Support</button></li>
              <li><button onClick={() => handleNavClick('contact')} className="hover:text-primary transition">Sales</button></li>
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}