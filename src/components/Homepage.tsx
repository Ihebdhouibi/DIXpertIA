import React, { useState } from 'react';

interface HomepageProps {
  onLoginClick: () => void;
  showDashboardButton?: boolean;
}

type Page = 'home' | 'services' | 'about' | 'contact';

export default function Homepage({ onLoginClick, showDashboardButton }: HomepageProps) {
  const [currentPage, setCurrentPage] = useState<Page>('home');

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

  const faqs = [
    { q: 'What types of cloud services do you offer?', a: 'We provide IaaS, PaaS, and SaaS solutions with a multi-cloud architecture (AWS, Azure, GCP) for optimal scalability.' },
    { q: 'How do you ensure the security of our data?', a: 'We apply ISO 27001 standards, regular audits, and advanced encryption protocols to protect your data.' },
    { q: 'What is your average support response time?', a: 'Our technical support responds within 4 hours for standard requests, and immediately for critical incidents (24/7 SLA).' },
    { q: 'Can we migrate an existing infrastructure without service interruption?', a: 'Yes, we plan phased migrations with failover testing to ensure business continuity.' },
    { q: 'How does your service pricing estimation work?', a: 'We conduct a preliminary audit of your needs, then provide a detailed quote with no obligation.' }
  ];

  // --- Contact Page ---
  if (currentPage === 'contact') {
    return (
      <div className="min-h-screen bg-white text-on-surface font-sans">
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

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <button
            onClick={() => handleNavClick('home')}
            className="inline-flex items-center gap-2 text-body-sm text-outline hover:text-primary transition mb-8"
          >
            ← Back to Home
          </button>

          <h1 className="text-h1 font-black text-on-surface mb-2">Contact Our Experts</h1>
          <p className="text-body-lg text-on-surface-variant mb-12 max-w-3xl">
            Whether you want a full system audit or to initiate a migration, our on‑call architects
            are ready to respond within 4 hours.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
            {/* Left: Contact Info */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/30">
                <h3 className="font-bold text-body-sm text-on-surface mb-4">Our Contact Details</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-caption font-semibold text-on-surface-variant">Emergency Assistance (SLA)</p>
                    <p className="text-body-sm font-bold text-on-surface">+33 (0) 1 45 88 90 22</p>
                    <p className="text-caption text-on-surface-variant">24/7 emergency line for subscribed clients</p>
                  </div>
                  <div>
                    <p className="text-caption font-semibold text-on-surface-variant">Business Integration Inquiries</p>
                    <p className="text-body-sm font-bold text-on-surface">contact@dixpertia.com</p>
                    <p className="text-caption text-on-surface-variant">Guaranteed response within 4 business hours</p>
                  </div>
                  <div>
                    <p className="text-caption font-semibold text-on-surface-variant">Technical Headquarters</p>
                    <p className="text-body-sm text-on-surface">DIXpertIA SAS</p>
                    <p className="text-body-sm text-on-surface">86 Boulevard Haussmann, 75008 Paris, France</p>
                  </div>
                  <div>
                    <p className="text-caption font-semibold text-on-surface-variant">On‑Call Office Uptime</p>
                    <p className="text-body-sm text-on-surface">Monday – Friday: 8:00 AM – 7:00 PM</p>
                    <p className="text-body-sm text-on-surface">Active network crisis team 24/7/365</p>
                  </div>
                </div>
              </div>

              <div className="bg-primary-container/20 p-4 rounded-lg border border-primary/20 text-center">
                <span className="text-xs font-black uppercase text-primary tracking-wider">REPLY SLA: 4h</span>
              </div>
            </div>

            {/* Right: Contact Form */}
            <div className="lg:col-span-3 bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/30">
              <h3 className="font-bold text-body-lg text-on-surface mb-6">Inquiry Registration Form</h3>
              <form className="space-y-5">
                <div>
                  <label className="block text-caption font-semibold text-on-surface-variant mb-1">Full Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Alexandre Dubois"
                    className="w-full px-4 py-2.5 border border-outline-variant rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none transition bg-white text-body-sm text-on-surface placeholder:text-outline"
                  />
                </div>
                <div>
                  <label className="block text-caption font-semibold text-on-surface-variant mb-1">Email Address</label>
                  <input
                    type="email"
                    placeholder="e.g. a.dubois@innovate.fr"
                    className="w-full px-4 py-2.5 border border-outline-variant rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none transition bg-white text-body-sm text-on-surface placeholder:text-outline"
                  />
                </div>
                <div>
                  <label className="block text-caption font-semibold text-on-surface-variant mb-1">Consultation Topic</label>
                  <input
                    type="text"
                    placeholder="e.g. Security audit / Penetration testing"
                    className="w-full px-4 py-2.5 border border-outline-variant rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none transition bg-white text-body-sm text-on-surface placeholder:text-outline"
                  />
                </div>
                <div>
                  <label className="block text-caption font-semibold text-on-surface-variant mb-1">Message / Technical Context</label>
                  <textarea
                    rows={4}
                    placeholder="Briefly describe your company's existing infrastructure, performance goals, or specific regulatory requirements..."
                    className="w-full px-4 py-2.5 border border-outline-variant rounded-lg focus:border-primary focus:ring-1 focus:ring-primary outline-none transition bg-white text-body-sm text-on-surface placeholder:text-outline resize-none"
                  />
                </div>
                <button
                  type="submit"
                  className="bg-primary text-white px-6 py-3 rounded-lg font-bold hover:bg-primary/95 transition shadow-sm"
                >
                  Submit to Technical Team
                </button>
              </form>
            </div>
          </div>

          {/* FAQ Section */}
          <section className="mt-16 border-t border-outline-variant/30 pt-12">
            <h2 className="text-h2 font-black text-on-surface text-center mb-8">Frequently Asked Questions</h2>
            <p className="text-body-sm text-on-surface-variant text-center mb-8">
              Search and filter our official answers instantly
            </p>
            <div className="max-w-3xl mx-auto space-y-4">
              {faqs.map((faq, idx) => (
                <div key={idx} className="bg-surface-container-lowest p-4 rounded-lg border border-outline-variant/30">
                  <h4 className="font-bold text-body-sm text-on-surface">{faq.q}</h4>
                  <p className="text-body-sm text-on-surface-variant mt-1">{faq.a}</p>
                </div>
              ))}
            </div>
          </section>
        </main>

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

  // --- Default Homepage with sections ---
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