import { defineMessages } from '../define';

/**
 * home: the public website, homepage and contact page. See ../define.ts; keys
 * start with "home.". French is written for the reader, not word for word,
 * and kept close to the English length so the layout holds at 390px. Labels
 * in fixed-width columns (console rows, phase bars) are kept short on purpose.
 */
export default defineMessages('home', {
  // Header and navigation
  'home.nav.primary': { fr: 'Navigation principale', en: 'Primary' },
  'home.nav.homeLink': { fr: 'DI Xpertia, accueil', en: 'DI Xpertia, home' },
  'home.nav.home': { fr: 'Accueil', en: 'Home' },
  'home.nav.services': { fr: 'Services', en: 'Services' },
  'home.nav.about': { fr: 'À propos', en: 'About' },
  'home.nav.contact': { fr: 'Contact', en: 'Contact' },
  // The short label is part of the full one, which is the button's name at
  // every width (WCAG 2.5.3, label in name).
  'home.nav.dashboard': { fr: 'Accéder à mon espace', en: 'Go to Dashboard' },
  /** The same button on a phone, where the full label does not fit beside the toggle. */
  'home.nav.dashboardShort': { fr: 'Mon espace', en: 'Dashboard' },

  // Hero
  'home.hero.headline': {
    fr: 'L’intelligence numérique, conçue par des experts.',
    en: 'Digital intelligence, expertly engineered.',
  },
  'home.hero.disciplines': {
    fr: 'Cloud · Cybersécurité · Logiciel sur mesure',
    en: 'Cloud · Cybersecurity · Custom software',
  },
  'home.hero.coordinates': {
    fr: '36,45° N  10,73° E — Nabeul',
    en: '36.45° N  10.73° E — Nabeul',
  },
  'home.hero.lead': {
    fr: 'Nous concevons, construisons et exploitons les systèmes dont dépend votre organisation : infrastructure cloud, sécurité et logiciels, pensés pour la fiabilité dès la première ligne.',
    en: 'We design, build and run the systems your organisation depends on — cloud infrastructure, security and software, engineered for reliability from the first line.',
  },
  'home.hero.contact': { fr: 'Nous contacter', en: 'Contact us' },
  'home.hero.services': { fr: 'Nos services', en: 'Our services' },

  // "How we work" console. Status words fit a 96px column: 13 characters at most.
  'home.console.label': {
    fr: 'Illustration de notre méthode : planifier, provisionner, sécuriser, tester, déployer et superviser',
    en: 'Illustration of how we work: plan, provision, harden, test, deploy and monitor',
  },
  'home.console.title': { fr: 'notre méthode', en: 'how we work' },
  'home.console.queued': { fr: 'en attente', en: 'queued' },
  'home.console.cloud': { fr: 'Cloud', en: 'Cloud' },
  'home.console.cloudWorking': { fr: 'création', en: 'provisioning' },
  'home.console.cloudDone': { fr: 'en ligne', en: 'healthy' },
  'home.console.security': { fr: 'Sécurité', en: 'Security' },
  'home.console.securityWorking': { fr: 'analyse', en: 'scanning' },
  'home.console.securityDone': { fr: 'protégé', en: 'protected' },
  'home.console.software': { fr: 'Logiciel', en: 'Software' },
  'home.console.softwareWorking': { fr: 'compilation', en: 'building' },
  'home.console.softwareDone': { fr: 'livré', en: 'shipped' },
  'home.console.log1': { fr: '› planifier l’infrastructure', en: '› plan infrastructure' },
  'home.console.log2': { fr: '› provisionner le réseau … ok', en: '› provision network … ok' },
  'home.console.log3': { fr: '› durcir les accès … ok', en: '› harden access policies … ok' },
  'home.console.log4': { fr: '› lancer les tests … ok', en: '› run test suite … ok' },
  'home.console.log5': { fr: '› déployer la version … ok', en: '› deploy release … ok' },
  'home.console.log6': { fr: '› superviser · systèmes nominaux', en: '› monitor · all systems nominal' },

  // Services
  'home.services.eyebrow': { fr: '01 — Services', en: '01 — Services' },
  'home.services.title': { fr: 'Ce que nous faisons', en: 'What we do' },
  'home.services.note': {
    fr: 'Trois disciplines, une seule équipe : le cloud, la sécurité et le code sont pensés ensemble.',
    en: 'Three disciplines, one team — so the cloud, the security and the code are designed together.',
  },
  /** A service row's accessible name: the row is a button to the contact page. */
  'home.services.itemLabel': { fr: '{title} : {desc} Nous contacter', en: '{title}: {desc} Contact us' },
  'home.services.cloud.title': { fr: 'Infrastructure cloud', en: 'Cloud Infrastructure' },
  'home.services.cloud.tags': {
    fr: 'Architecture · Migration · Exploitation',
    en: 'Architecture · Migration · Operations',
  },
  'home.services.cloud.desc': {
    fr: 'Une architecture cloud évolutive et sécurisée, conçue pour la haute disponibilité et les exigences de l’entreprise.',
    en: 'Scalable, secure cloud architecture designed for high availability and enterprise performance.',
  },
  'home.services.security.title': { fr: 'Cybersécurité', en: 'Cybersecurity' },
  'home.services.security.tags': { fr: 'Audit · Durcissement · Conformité', en: 'Audit · Hardening · Compliance' },
  'home.services.security.desc': {
    fr: 'Protection contre les menaces et pilotage de la conformité, pour garder vos données critiques en sécurité.',
    en: 'Threat protection and compliance management that keeps your critical data assets safe.',
  },
  'home.services.software.title': { fr: 'Logiciel sur mesure', en: 'Custom Software' },
  'home.services.software.tags': { fr: 'Web · Mobile · Intégrations', en: 'Web · Mobile · Integrations' },
  'home.services.software.desc': {
    fr: 'Des applications sur mesure, construites autour de vos processus métier — et non l’inverse.',
    en: 'Bespoke applications built around your operational workflows — not the other way round.',
  },

  // Engagement models
  'home.engage.eyebrow': { fr: '02 — Collaboration', en: '02 — Engagement' },
  'home.engage.title': { fr: 'Nos modes de collaboration', en: 'Ways to work with us' },
  'home.engage.note': {
    fr: 'Choisissez votre niveau d’implication. Nous adaptons le modèle, jamais l’exigence.',
    en: 'Choose how involved you want to be. We adapt the model, not the standard.',
  },
  'home.engage.tablist': { fr: 'Modèles de collaboration', en: 'Engagement models' },
  'home.engage.bestFor': { fr: 'IDÉAL POUR → ', en: 'BEST FOR → ' },
  'home.engage.whoLeads': { fr: 'Qui pilote chaque phase', en: 'Who leads each phase' },
  'home.engage.legendTeam': { fr: 'Votre équipe', en: 'Your team' },
  /** The phase chart for screen readers: {phases} is "Scope, joint; Build, DI Xpertia; ..." */
  'home.engage.chartLabel': {
    fr: 'Qui pilote chaque phase en {model} : {phases}. {footnote}',
    en: 'Who leads each phase in {model}: {phases}. {footnote}',
  },
  'home.engage.lead.team': { fr: 'votre équipe', en: 'your team' },
  'home.engage.lead.joint': { fr: 'partagé', en: 'joint' },
  'home.engage.lead.us': { fr: 'DI Xpertia', en: 'DI Xpertia' },
  // Phase names sit in a 96px column, uppercase: 11 characters at most.
  'home.engage.phase.scope': { fr: 'Cadrage', en: 'Scope' },
  'home.engage.phase.build': { fr: 'Réalisation', en: 'Build' },
  'home.engage.phase.launch': { fr: 'Lancement', en: 'Launch' },
  'home.engage.phase.run': { fr: 'Opérations', en: 'Run' },

  'home.engage.project.name': { fr: 'Projet clé en main', en: 'Project delivery' },
  'home.engage.project.headline': {
    fr: 'Vous fixez l’objectif. Nous le livrons, de bout en bout.',
    en: 'You define the outcome. We deliver it, end to end.',
  },
  'home.engage.project.desc': {
    fr: 'Un périmètre défini, une équipe dédiée et un calendrier clair. Architecture, développement, sécurité, mise en production : nous prenons tout en charge, puis vous remettons un système documenté qui vous appartient.',
    en: 'A fixed scope, a dedicated team and a clear timeline. We handle architecture, build, security and launch, then hand over a documented system you fully own.',
  },
  'home.engage.project.item1': {
    fr: 'Atelier de cadrage et cahier des charges écrit',
    en: 'Scoping workshop and written specification',
  },
  'home.engage.project.item2': {
    fr: 'Une équipe dédiée, un seul référent technique',
    en: 'Dedicated team with a single technical lead',
  },
  'home.engage.project.item3': {
    fr: 'Revue de sécurité avant chaque mise en production',
    en: 'Security reviewed before every release',
  },
  'home.engage.project.item4': {
    fr: 'Documentation complète et passation — le code est à vous',
    en: 'Full documentation and handover — the code is yours',
  },
  'home.engage.project.fit': {
    fr: 'Une nouvelle plateforme, une migration ou un produit bien défini.',
    en: 'A new platform, a migration or a well-defined product.',
  },
  'home.engage.project.footnote': {
    fr: 'Nous pilotons la réalisation ; vous validez chaque jalon.',
    en: 'We lead delivery; you validate at each milestone.',
  },

  'home.engage.extension.name': { fr: 'Renfort d’équipe', en: 'Team extension' },
  'home.engage.extension.headline': {
    fr: 'Des ingénieurs seniors, intégrés à votre équipe.',
    en: 'Senior engineers, embedded in your team.',
  },
  'home.engage.extension.desc': {
    fr: 'Votre feuille de route, vos rituels, vos outils. Nos ingénieurs rejoignent votre équipe pour apporter la capacité ou l’expertise qui vous manque en interne : cloud, sécurité ou logiciel.',
    en: 'Your roadmap, your rituals, your tools. Our engineers join your team to add capacity or expertise you don’t have in-house — cloud, security or software.',
  },
  'home.engage.extension.item1': {
    fr: 'Des profils adaptés à votre stack et au niveau recherché',
    en: 'Engineers matched to your stack and seniority needs',
  },
  'home.engage.extension.item2': {
    fr: 'Travail dans vos outils, vos sprints et vos revues de code',
    en: 'Work inside your tools, sprints and code review',
  },
  'home.engage.extension.item3': {
    fr: 'Transfert de compétences prévu dès le départ',
    en: 'Knowledge transfer built into the engagement',
  },
  'home.engage.extension.item4': {
    fr: 'Une équipe qui s’ajuste à votre feuille de route',
    en: 'Scale up or down as your roadmap changes',
  },
  'home.engage.extension.fit': {
    fr: 'Les équipes qui doivent accélérer sans recruter.',
    en: 'Teams that need to move faster without hiring.',
  },
  'home.engage.extension.footnote': {
    fr: 'Vous pilotez la feuille de route ; nous renforçons l’exécution.',
    en: 'You lead the roadmap; we strengthen execution.',
  },

  'home.engage.managed.name': { fr: 'Infogérance', en: 'Managed operations' },
  'home.engage.managed.headline': {
    fr: 'Nous assurons le run, votre équipe construit.',
    en: 'We run it, so your team can build.',
  },
  'home.engage.managed.desc': {
    fr: 'L’exploitation continue de votre cloud et de vos applications : supervision, mises à jour, correctifs de sécurité et réponse aux incidents, avec des comptes rendus réguliers sur ce que nous faisons et pourquoi.',
    en: 'Ongoing operation of your cloud and applications: monitoring, updates, security patches and incident response, with regular reporting on what we did and why.',
  },
  'home.engage.managed.item1': {
    fr: 'Supervision et alertes sur l’ensemble de vos systèmes',
    en: 'Monitoring and alerting across your systems',
  },
  'home.engage.managed.item2': {
    fr: 'Correctifs de sécurité et revues des accès',
    en: 'Security patching and access reviews',
  },
  'home.engage.managed.item3': {
    fr: 'Réponse aux incidents et rapports post-incident',
    en: 'Incident response and post-incident reports',
  },
  'home.engage.managed.item4': {
    fr: 'Revues régulières des coûts, des risques et des performances',
    en: 'Regular reviews of cost, risk and performance',
  },
  'home.engage.managed.fit': {
    fr: 'Les systèmes qui doivent rester disponibles, sûrs et à jour.',
    en: 'Systems that must stay up, secure and up to date.',
  },
  'home.engage.managed.footnote': {
    fr: 'Nous gérons le quotidien ; vous gardez visibilité et contrôle.',
    en: 'We run day to day; you keep full visibility and control.',
  },

  // Closing call to action
  'home.cta.eyebrow': { fr: '03 — À propos', en: '03 — About' },
  'home.cta.title': {
    fr: 'Prêt à transformer votre infrastructure informatique ?',
    en: 'Ready to transform your IT infrastructure?',
  },
  'home.cta.lead': {
    fr: 'Faites équipe avec DI Xpertia pour doter votre organisation de technologies modernes et fiables.',
    en: 'Partner with DI Xpertia to bring modern, reliable technology to your organisation.',
  },
  'home.cta.button': { fr: 'Démarrons ensemble', en: 'Get started today' },

  // Footer
  'home.footer.taglineLine1': { fr: 'Intelligence numérique,', en: 'Digital intelligence,' },
  'home.footer.taglineLine2': { fr: 'conçue par des experts', en: 'expertly engineered' },
  'home.footer.company': { fr: 'Société', en: 'Company' },
  'home.footer.aboutUs': { fr: 'Qui sommes-nous', en: 'About us' },
  'home.footer.links': { fr: 'Liens', en: 'Links' },
  'home.footer.contact': { fr: 'Contact', en: 'Contact' },
  'home.footer.support': { fr: 'Assistance', en: 'Support' },
  'home.footer.sales': { fr: 'Commercial', en: 'Sales' },
  'home.footer.city': { fr: '8011 Nabeul, Tunisie', en: '8011 Nabeul, Tunisia' },
  'home.footer.rights': {
    fr: '© {year} DI Xpertia SUARL. Tous droits réservés.',
    en: '© {year} DI Xpertia SUARL. All rights reserved.',
  },

  // Contact page
  'home.contact.back': { fr: 'Retour à l’accueil', en: 'Back to Home' },
  'home.contact.eyebrow': { fr: 'Contact', en: 'Contact' },
  'home.contact.title': { fr: 'Contactez nos experts', en: 'Contact our experts' },
  'home.contact.intro': {
    fr: 'Audit complet de vos systèmes ou projet de migration : parlez-nous de votre projet, notre équipe vous répondra rapidement.',
    en: 'Whether you want a full system audit or to start a migration, tell us about your project and our team will get back to you quickly.',
  },
  'home.contact.details': { fr: 'Nos coordonnées', en: 'Our contact details' },
  'home.contact.phone': { fr: 'Téléphone', en: 'Phone' },
  'home.contact.phoneNote': {
    fr: 'Pour les demandes urgentes, aux heures de bureau',
    en: 'For urgent requests, during office hours',
  },
  'home.contact.business': { fr: 'Demandes commerciales', en: 'Business Inquiries' },
  'home.contact.businessNote': {
    fr: 'Nous répondons généralement sous un jour ouvré',
    en: 'We usually reply within one business day',
  },
  'home.contact.headquarters': { fr: 'Siège technique', en: 'Technical Headquarters' },
  'home.contact.address': {
    fr: 'DI Xpertia SUARL · Rue de Pasteur, Dar Chaabane El Fehri, 8011 Nabeul, Tunisie',
    en: 'DI Xpertia SUARL · Rue de Pasteur, Dar Chaabane El Fehri, 8011 Nabeul, Tunisia',
  },
  'home.contact.hours': { fr: 'Horaires d’ouverture', en: 'Office Hours' },
  'home.contact.hoursValue': {
    fr: 'Du lundi au vendredi : 8 h – 19 h',
    en: 'Monday – Friday: 8:00 AM – 7:00 PM',
  },

  'home.contact.form.title': { fr: 'Formulaire de demande', en: 'Inquiry registration form' },
  'home.contact.form.sent': { fr: 'Merci, votre message a bien été envoyé.', en: 'Thank you, your message has been sent.' },
  'home.contact.form.sentHint': {
    fr: 'Notre équipe l’a bien reçu et vous répondra par e-mail.',
    en: 'Our team has received it and will get back to you by e-mail.',
  },
  'home.contact.form.name': { fr: 'Nom complet *', en: 'Full Name *' },
  'home.contact.form.namePlaceholder': { fr: 'ex. Alexandre Dubois', en: 'e.g. Alexandre Dubois' },
  'home.contact.form.email': { fr: 'Adresse e-mail *', en: 'Email Address *' },
  'home.contact.form.emailPlaceholder': { fr: 'ex. a.dubois@innovate.fr', en: 'e.g. a.dubois@innovate.fr' },
  'home.contact.form.topic': { fr: 'Objet de votre demande *', en: 'Consultation Topic *' },
  'home.contact.form.topic.security_audit': {
    fr: 'Audit de sécurité / test d’intrusion',
    en: 'Security audit / Penetration testing',
  },
  'home.contact.form.topic.cloud_migration': {
    fr: 'Migration vers un cloud hybride',
    en: 'Hybrid Cloud Migration Planning',
  },
  'home.contact.form.topic.custom_development': {
    fr: 'Développement API / CRM sur mesure',
    en: 'Custom API / CRM Development',
  },
  'home.contact.form.topic.support_subscription': { fr: 'Abonnement de support', en: 'Support Subscription' },
  'home.contact.form.topic.other': { fr: 'Autre demande technique', en: 'Other Technology Request' },
  'home.contact.form.message': { fr: 'Message / contexte technique *', en: 'Message / Technical Context *' },
  'home.contact.form.messagePlaceholder': {
    fr: 'Décrivez brièvement votre infrastructure actuelle, vos objectifs de performance ou vos contraintes réglementaires...',
    en: "Briefly describe your company's existing infrastructure, performance goals, or specific regulatory requirements...",
  },
  'home.contact.form.sending': { fr: 'Envoi en cours…', en: 'Sending...' },
  'home.contact.form.submit': { fr: 'Envoyer à l’équipe technique', en: 'Submit to Technical Team' },

  'home.contact.error.name': { fr: 'Veuillez saisir votre nom complet.', en: 'Please enter your full name.' },
  'home.contact.error.email': {
    fr: 'Veuillez saisir une adresse e-mail valide.',
    en: 'Please enter a valid email address.',
  },
  'home.contact.error.messageLength': {
    fr: 'Votre message doit contenir au moins 10 caractères.',
    en: 'Your message must be at least 10 characters.',
  },
  'home.contact.error.tooMany': {
    fr: 'Nous avons reçu de nombreux messages au cours de la dernière heure. Veuillez réessayer plus tard, ou appelez-nous au {phone}.',
    en: 'We received many messages in the last hour. Please try again later, or call us on {phone}.',
  },
  'home.contact.error.invalid': {
    fr: 'Veuillez vérifier les champs : une adresse e-mail valide et un message de 10 à 5 000 caractères.',
    en: 'Please check the fields: a valid e-mail, and a message of 10 to 5,000 characters.',
  },
  'home.contact.error.notSent': {
    fr: 'Votre message n’a pas pu être envoyé. Veuillez réessayer, ou appelez-nous au {phone}.',
    en: 'Your message could not be sent. Please try again, or call us on {phone}.',
  },

  // FAQ. Worded without guarantees the company has not committed to: no
  // response times, no 24/7 line, no certification (#98).
  'home.faq.title': { fr: 'Questions fréquentes', en: 'Frequently asked questions' },
  'home.faq.subtitle': {
    fr: 'Recherchez et filtrez nos réponses officielles en un instant',
    en: 'Search and filter our official answers instantly',
  },
  'home.faq.search': { fr: 'Rechercher (ex. sécurité, migration)...', en: 'Search (e.g. security, migration)...' },
  'home.faq.noResults': {
    fr: 'Aucun résultat pour « {query} ». Essayez une recherche plus large.',
    en: 'No results for "{query}". Please broaden your search.',
  },
  'home.faq.cloud.q': {
    fr: 'Quels types de services cloud proposez-vous ?',
    en: 'What types of cloud services do you offer?',
  },
  'home.faq.cloud.a': {
    fr: 'Nous proposons des solutions IaaS, PaaS et SaaS sur une architecture multicloud (AWS, Azure, GCP), pour une évolutivité optimale.',
    en: 'We provide IaaS, PaaS, and SaaS solutions with a multi-cloud architecture (AWS, Azure, GCP) for optimal scalability.',
  },
  'home.faq.security.q': {
    fr: 'Comment assurez-vous la sécurité de nos données ?',
    en: 'How do you ensure the security of our data?',
  },
  'home.faq.security.a': {
    fr: 'Nous suivons des pratiques de sécurité reconnues, comme celles de l’ISO 27001, avec des revues régulières et le chiffrement de vos données.',
    en: 'We follow recognised security practices, such as those of ISO 27001, with regular reviews and encryption of your data.',
  },
  'home.faq.response.q': {
    fr: 'Quel est votre délai moyen de réponse au support ?',
    en: 'What is your average support response time?',
  },
  'home.faq.response.a': {
    fr: 'Nous nous efforçons de répondre rapidement, généralement sous un jour ouvré, et traitons en priorité les incidents critiques.',
    en: 'We aim to reply quickly, usually within one business day, and we prioritise critical incidents.',
  },
  'home.faq.migration.q': {
    fr: 'Peut-on migrer une infrastructure existante sans interruption de service ?',
    en: 'Can we migrate an existing infrastructure without service interruption?',
  },
  'home.faq.migration.a': {
    fr: 'Dans la plupart des cas, oui : nous planifions des migrations progressives, avec des tests de bascule, pour que vos services restent disponibles.',
    en: 'In most cases, yes: we plan phased migrations with failover testing to keep your services running.',
  },
  'home.faq.pricing.q': {
    fr: 'Comment estimez-vous le coût de vos prestations ?',
    en: 'How does your service pricing estimation work?',
  },
  'home.faq.pricing.a': {
    fr: 'Nous réalisons d’abord un audit préliminaire de vos besoins, puis vous remettons un devis détaillé, sans engagement.',
    en: 'We conduct a preliminary audit of your needs, then provide a detailed quote with no obligation.',
  },
});
