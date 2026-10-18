"""French and English for everything the server writes (#135).

Every user-facing string the server produces - API errors, database rule
messages, notifications, e-mails, the invoice PDF, formatted dates - comes
from CATALOG below, in French and in English, side by side so a reviewer
reads each pair together.

Which language:
- an API response: the request's language. The UI sends it in
  Accept-Language; without one, French, the product's default.
- an e-mail or a notification's text: the recipient's `users.locale`.
- an invoice PDF: the client's `clients.locale`, so the same invoice always
  prints the same way, whoever downloads it.

Database triggers raise their messages in English (they are also read in SQL
sessions and logs). translate_db_message() recognises each one by its text and
returns the catalog's version; tests/test_i18n.py fails for a trigger message
with no pattern here.
"""

import re
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException

LOCALES = ("fr", "en")
DEFAULT_LOCALE = "fr"

_locale: ContextVar[str] = ContextVar("dixpertia_locale", default=DEFAULT_LOCALE)


def normalise(value: str | None) -> str:
    """'fr', 'fr-TN', 'en-US;q=0.9' -> a supported locale; anything else -> French."""
    if value:
        for part in value.split(","):
            tag = part.split(";")[0].strip().lower()[:2]
            if tag in LOCALES:
                return tag
    return DEFAULT_LOCALE


def set_locale(locale: str | None) -> None:
    _locale.set(normalise(locale))


def current_locale() -> str:
    return _locale.get()


# --- The catalog ------------------------------------------------------------------
# Named placeholders ({ref}) for messages the server builds, positional ones
# ({0}) for database messages, in the order the trigger's % appear.

CATALOG: dict[str, dict[str, str]] = {
    # Authentication and accounts
    "auth.not_authenticated": {"en": "Not authenticated", "fr": "Non authentifié"},
    "auth.forbidden": {"en": "Access denied", "fr": "Accès refusé"},
    "auth.admin_required": {"en": "Administrator role required", "fr": "Rôle administrateur requis"},
    "auth.invalid_credentials": {"en": "Invalid credentials", "fr": "Identifiants incorrects"},
    "auth.too_many_requests": {
        "en": "Too many attempts. Please wait a few minutes and try again.",
        "fr": "Trop de tentatives. Patientez quelques minutes, puis réessayez."},
    "auth.invalid_link": {
        "en": "This link is invalid or has expired. Ask for a new one.",
        "fr": "Ce lien est invalide ou a expiré. Demandez-en un nouveau."},
    "password.too_short": {
        "en": "The password must be at least {min} characters long.",
        "fr": "Le mot de passe doit contenir au moins {min} caractères."},
    "password.too_long": {
        "en": "The password must be at most {max} bytes long.",
        "fr": "Le mot de passe ne doit pas dépasser {max} octets."},
    "password.blank": {"en": "The password cannot be blank.", "fr": "Le mot de passe ne peut pas être vide."},
    "user.email_taken": {
        "en": "This e-mail address is already registered.",
        "fr": "Cette adresse e-mail est déjà utilisée."},
    "user.not_found": {"en": "User not found", "fr": "Utilisateur introuvable"},
    "user.already_activated": {"en": "This account is already activated.", "fr": "Ce compte est déjà activé."},
    "user.cannot_change_self": {
        "en": "You cannot change your own role or deactivate yourself.",
        "fr": "Vous ne pouvez ni changer votre propre rôle ni vous désactiver."},
    "account.activated": {
        "en": "Account activated. You can now sign in.",
        "fr": "Compte activé. Vous pouvez maintenant vous connecter."},
    "account.reset_sent": {
        "en": "If your email is registered, you will receive a password reset link.",
        "fr": "Si votre adresse est enregistrée, vous recevrez un lien de réinitialisation du mot de passe."},
    "account.password_updated": {"en": "Password updated successfully.", "fr": "Mot de passe mis à jour."},

    # Leave and employees
    "leave.end_before_start": {
        "en": "The end date cannot be before the start date.",
        "fr": "La date de fin ne peut pas précéder la date de début."},
    "leave.no_employee_record": {
        "en": "This account has no employee record, so it cannot request leave.",
        "fr": "Ce compte n'a pas de fiche employé : il ne peut pas demander de congé."},
    "leave.not_found": {"en": "Leave request not found", "fr": "Demande de congé introuvable"},
    "employee.already_exists": {
        "en": "This user already has an employee record.",
        "fr": "Cet utilisateur a déjà une fiche employé."},

    # Accounting, suppliers and invoices
    "period.already_closed": {
        "en": "The accounting period {month} is already closed and cannot be reopened.",
        "fr": "La période comptable {month} est déjà clôturée et ne peut pas être rouverte."},
    "supplier.name_taken": {
        "en": "A supplier named '{name}' already exists.",
        "fr": "Un fournisseur nommé « {name} » existe déjà."},
    "supplier.not_found": {"en": "Supplier not found", "fr": "Fournisseur introuvable"},
    "client.name_taken": {
        "en": "A client named '{name}' already exists.",
        "fr": "Un client nommé « {name} » existe déjà."},
    "client.not_found": {"en": "Client not found", "fr": "Client introuvable"},
    "supplier_invoice.duplicate": {
        "en": "Invoice '{ref}' from this supplier has already been recorded.",
        "fr": "La facture « {ref} » de ce fournisseur est déjà enregistrée."},
    "invoice.not_found": {"en": "Invoice not found", "fr": "Facture introuvable"},
    "invoice.supplier_bill_not_editable": {
        "en": "Invoice {ref} is a supplier bill; only invoices we issue can be edited.",
        "fr": "La facture {ref} est une facture fournisseur : seules nos factures peuvent être modifiées."},
    "invoice.not_a_draft": {
        "en": "Invoice {ref} is no longer a draft and cannot be edited; correct it with a new document.",
        "fr": "La facture {ref} n'est plus un brouillon et ne peut plus être modifiée ; "
              "corrigez-la par un nouveau document."},
    "invoice.under_review": {
        "en": "Invoice {ref} is under review and cannot be edited.",
        "fr": "La facture {ref} est en cours de vérification et ne peut pas être modifiée."},
    "invoice.due_before_issue": {
        "en": "The due date cannot be before the issue date.",
        "fr": "L'échéance ne peut pas précéder la date d'émission."},
    "invoice.supplier_bill_not_reviewed": {
        "en": "Invoice {ref} is a supplier bill; only invoices we issue are verified.",
        "fr": "La facture {ref} est une facture fournisseur : seules nos factures sont vérifiées."},
    "invoice.not_submittable": {
        "en": "Invoice {ref} is not a draft waiting to be submitted.",
        "fr": "La facture {ref} n'est pas un brouillon en attente de soumission."},
    "invoice.needs_a_line": {
        "en": "An invoice needs at least one line before it is submitted.",
        "fr": "Une facture doit comporter au moins une ligne avant d'être soumise."},
    "invoice.not_awaiting_review": {
        "en": "Invoice {ref} is not waiting for verification.",
        "fr": "La facture {ref} n'est pas en attente de vérification."},
    "invoice.no_self_approval": {
        "en": "An invoice is never approved by the person who created it.",
        "fr": "Une facture n'est jamais approuvée par la personne qui l'a créée."},
    "invoice.no_self_rejection": {
        "en": "An invoice is never rejected by the person who created it.",
        "fr": "Une facture n'est jamais rejetée par la personne qui l'a créée."},
    "invoice.due_before_today": {
        "en": "Invoice {ref} is due {due}, before today's issue date; reject it so the due date can be corrected.",
        "fr": "La facture {ref} est échue le {due}, avant la date d'émission d'aujourd'hui ; "
              "rejetez-la pour que l'échéance soit corrigée."},
    "invoice.already_left_draft": {
        "en": "Invoice {ref} has already left draft.",
        "fr": "La facture {ref} n'est déjà plus un brouillon."},
    "invoice.send_before_approval": {
        "en": "Invoice {ref} cannot be sent before the accountant approves it.",
        "fr": "La facture {ref} ne peut pas être envoyée avant l'approbation du comptable."},
    "invoice.not_payable": {
        "en": "Invoice {ref} is {status} and cannot be marked paid; only a sent invoice can.",
        "fr": "La facture {ref} est {status} et ne peut pas être marquée payée ; "
              "seule une facture envoyée peut l'être."},
    "payment.in_future": {
        "en": "The payment date cannot be in the future.",
        "fr": "La date de paiement ne peut pas être dans le futur."},
    "payment.before_issue": {
        "en": "The payment date cannot be before the issue date, {date}.",
        "fr": "La date de paiement ne peut pas précéder la date d'émission, le {date}."},
    "invoice.not_cancellable": {
        "en": "Invoice {ref} is {status} and cannot be cancelled.",
        "fr": "La facture {ref} est {status} et ne peut pas être annulée."},
    "invoice.cancel_under_review": {
        "en": "Invoice {ref} is waiting for verification; the accountant approves or rejects it "
              "before it can be cancelled.",
        "fr": "La facture {ref} est en attente de vérification ; le comptable doit l'approuver ou la rejeter "
              "avant qu'elle puisse être annulée."},
    "invoice.cancel_closed_month": {
        "en": "Invoice {ref} belongs to a closed month and cannot be cancelled; "
              "correct it with a credit note in the open month.",
        "fr": "La facture {ref} appartient à un mois clôturé et ne peut pas être annulée ; "
              "corrigez-la par un avoir dans le mois ouvert."},
    "notification.not_found": {"en": "Notification not found", "fr": "Notification introuvable"},
    "db.refused": {
        "en": "The change was refused by a data rule.",
        "fr": "La modification a été refusée par une règle de données."},

    # Statuses inside sentences ("invoice X is {status}")
    "status.brouillon": {"en": "a draft", "fr": "un brouillon"},
    # Without the article, where a status is named rather than described:
    # "cannot go from draft to paid".
    "status_bare.brouillon": {"en": "draft", "fr": "brouillon"},
    "status.envoyee": {"en": "sent", "fr": "envoyée"},
    "status.payee": {"en": "paid", "fr": "payée"},
    "status.en_retard": {"en": "overdue", "fr": "en retard"},
    "status.annulee": {"en": "cancelled", "fr": "annulée"},
    "status.not_submitted": {"en": "not submitted", "fr": "non soumise"},
    "status.submitted": {"en": "submitted", "fr": "soumise"},
    "status.approved": {"en": "approved", "fr": "approuvée"},
    "status.rejected": {"en": "rejected", "fr": "rejetée"},

    # Database rule messages, recognised by DB_PATTERNS below
    "db.number_breaks_named_series": {
        "en": "Invoice number {0} breaks the {1} series: {2} was expected.",
        "fr": "Le numéro de facture {0} rompt la série {1} : {2} était attendu."},
    "db.number_breaks_series": {
        "en": "Invoice number {0} breaks the series: {1} was expected.",
        "fr": "Le numéro de facture {0} rompt la série : {1} était attendu."},
    "db.number_is_final": {
        "en": "Invoice {0} already has its legal number; it cannot change.",
        "fr": "La facture {0} a déjà son numéro légal ; il ne peut pas changer."},
    "db.number_on_approval": {
        "en": "Draft {0} gets its legal number only when the accountant approves it.",
        "fr": "Le brouillon {0} ne reçoit son numéro légal qu'à l'approbation du comptable."},
    "db.review_closed": {
        "en": "Invoice {0} is no longer a draft; its review is closed.",
        "fr": "La facture {0} n'est plus un brouillon ; sa vérification est close."},
    "db.review_transition": {
        "en": "Invoice {0} cannot go from {1} to {2} in review.",
        "fr": "La facture {0} ne peut pas passer de « {1} » à « {2} » en vérification."},
    "db.send_before_approval": {
        "en": "Invoice {0} cannot be sent before the accountant approves it.",
        "fr": "La facture {0} ne peut pas être envoyée avant l'approbation du comptable."},
    "db.books_after_sending": {
        "en": "Invoice {0} is still a draft; bookkeeping starts when it is sent.",
        "fr": "La facture {0} est encore un brouillon ; la comptabilisation commence à son envoi."},
    "db.not_editable_in_review": {
        "en": "Invoice {0} is under review or no longer a draft and cannot be edited.",
        "fr": "La facture {0} est en vérification ou n'est plus un brouillon, et ne peut pas être modifiée."},
    "db.not_editable": {
        "en": "Invoice {0} is no longer a draft and cannot be edited; correct it with a new document.",
        "fr": "La facture {0} n'est plus un brouillon et ne peut plus être modifiée ; "
              "corrigez-la par un nouveau document."},
    "db.line_move_in_review": {
        "en": "A line cannot be moved out of an invoice that is under review or no longer a draft.",
        "fr": "Une ligne ne peut pas être retirée d'une facture en vérification ou qui n'est plus un brouillon."},
    "db.line_move": {
        "en": "A line cannot be moved out of an invoice that is no longer a draft.",
        "fr": "Une ligne ne peut pas être retirée d'une facture qui n'est plus un brouillon."},
    "db.lines_archived": {
        "en": "Invoice {0} is archived and its lines are read-only; correct it with a new document in the open month.",
        "fr": "La facture {0} est archivée et ses lignes sont en lecture seule ; "
              "corrigez-la par un nouveau document dans le mois ouvert."},
    "db.lines_in_review": {
        "en": "Invoice {0} is under review or no longer a draft; its lines cannot be changed.",
        "fr": "La facture {0} est en vérification ou n'est plus un brouillon ; "
              "ses lignes ne peuvent pas être modifiées."},
    "db.lines_not_draft": {
        "en": "Invoice {0} is no longer a draft and its lines cannot be changed; correct it with a new document.",
        "fr": "La facture {0} n'est plus un brouillon et ses lignes ne peuvent pas être modifiées ; "
              "corrigez-la par un nouveau document."},
    "db.review_history_append_only": {
        "en": "The review history is append-only.",
        "fr": "L'historique de vérification ne peut qu'être complété."},
    "db.no_self_review": {
        "en": "An invoice is never approved or rejected by the person who created it.",
        "fr": "Une facture n'est jamais approuvée ni rejetée par la personne qui l'a créée."},
    "db.number_before_date": {
        "en": "Invoice {0} dated {1} would come before {2}, which is numbered lower but dated {3}. "
              "Invoice numbers must follow issue dates.",
        "fr": "La facture {0} datée du {1} viendrait avant {2}, numérotée plus bas mais datée du {3}. "
              "Les numéros de facture doivent suivre les dates d'émission."},
    "db.number_after_date": {
        "en": "Invoice {0} dated {1} would come after {2}, which is numbered higher but dated {3}. "
              "Invoice numbers must follow issue dates.",
        "fr": "La facture {0} datée du {1} viendrait après {2}, numérotée plus haut mais datée du {3}. "
              "Les numéros de facture doivent suivre les dates d'émission."},
    "db.archived_no_delete": {
        "en": "Invoice {0} belongs to a closed month and cannot be deleted; "
              "issue a credit note in the open month instead.",
        "fr": "La facture {0} appartient à un mois clôturé et ne peut pas être supprimée ; "
              "émettez plutôt un avoir dans le mois ouvert."},
    "db.archived_processing": {
        "en": "Invoice {0} is archived; its month is closed and the processing status cannot move back.",
        "fr": "La facture {0} est archivée ; son mois est clôturé et son statut de traitement "
              "ne peut pas revenir en arrière."},
    "db.archived_read_only": {
        "en": "Invoice {0} is archived and read-only; correct it with a new document in the open month.",
        "fr": "La facture {0} est archivée et en lecture seule ; "
              "corrigez-la par un nouveau document dans le mois ouvert."},
    "db.status_final": {
        "en": "Invoice {0} is {1} and final.",
        "fr": "La facture {0} est {1} et définitive."},
    "db.status_transition": {
        "en": "Invoice {0} cannot go from {1} to {2}.",
        "fr": "La facture {0} ne peut pas passer de « {1} » à « {2} »."},
    "db.cancel_under_review": {
        "en": "Invoice {0} is waiting for verification; the accountant approves or rejects it "
              "before it can be cancelled.",
        "fr": "La facture {0} est en attente de vérification ; le comptable doit l'approuver ou la rejeter "
              "avant qu'elle puisse être annulée."},
    "db.cancel_closed_month": {
        "en": "Invoice {0} belongs to a closed month and cannot be cancelled; "
              "correct it with a credit note in the open month.",
        "fr": "La facture {0} appartient à un mois clôturé et ne peut pas être annulée ; "
              "corrigez-la par un avoir dans le mois ouvert."},
    "db.paid_in_future": {
        "en": "Invoice {0} cannot be paid on {1}, a date in the future.",
        "fr": "La facture {0} ne peut pas être payée le {1}, une date future."},
    "db.period_closed": {
        "en": "The accounting period {0} is closed; an invoice cannot be dated into it. "
              "Issue it in the open month instead.",
        "fr": "La période comptable {0} est clôturée ; aucune facture ne peut y être datée. "
              "Émettez-la dans le mois ouvert."},
    "db.never_deleted": {
        "en": "Invoice {0} cannot be deleted: its number is part of a gapless series. "
              "Cancel it instead, which keeps the row and the number.",
        "fr": "La facture {0} ne peut pas être supprimée : son numéro fait partie d'une série sans trou. "
              "Annulez-la plutôt, ce qui conserve la ligne et le numéro."},
    "db.audit_append_only": {
        "en": "Audit event {0} cannot be changed or deleted: the audit trail is append-only.",
        "fr": "L'événement d'audit {0} ne peut être ni modifié ni supprimé : "
              "la piste d'audit ne peut qu'être complétée."},
    "db.leave_self_validation": {
        "en": "An employee cannot validate their own leave request.",
        "fr": "Un employé ne peut pas valider sa propre demande de congé."},

    # Notifications, rendered from their kind and parameters
    "notification.contact_request": {
        "en": "New enquiry from {name} about {topic_label}.",
        "fr": "Nouvelle demande de {name} : {topic_label}."},
    "notification.invoice_submitted": {
        "en": "Invoice {ref} for {party} is waiting for your verification.",
        "fr": "La facture {ref} pour {party} attend votre vérification."},
    "notification.invoice_approved": {
        "en": "Invoice {ref} for {party} was approved and can be sent.",
        "fr": "La facture {ref} pour {party} a été approuvée et peut être envoyée."},
    "notification.invoice_rejected": {
        "en": "Invoice {ref} for {party} was rejected: {comment}",
        "fr": "La facture {ref} pour {party} a été rejetée : {comment}"},
    "notification.invoice_cancelled": {
        "en": "Invoice {ref} for {party} was cancelled: {reason}. It needs a credit note in the books.",
        "fr": "La facture {ref} pour {party} a été annulée : {reason}. Elle doit être compensée par un avoir "
              "en comptabilité."},
    "notification.reminder_draft": {
        "en": "Invoice {ref} for {party} has been a draft for {span}. Submit it to the accountant when it is ready.",
        "fr": "La facture {ref} pour {party} est un brouillon depuis {span}. Soumettez-la au comptable "
              "lorsqu'elle est prête."},
    "notification.reminder_review": {
        "en": "Invoice {ref} for {party} has been waiting for your verification for {span}.",
        "fr": "La facture {ref} pour {party} attend votre vérification depuis {span}."},
    "notification.reminder_rejected": {
        "en": "Invoice {ref} for {party} was rejected {span} ago and has not been corrected. Correct and resubmit it.",
        "fr": "La facture {ref} pour {party} a été rejetée il y a {span} et n'a pas été corrigée. "
              "Corrigez-la puis soumettez-la à nouveau."},
    "notification.reminder_approved": {
        "en": "Invoice {ref} for {party} was approved {span} ago and has not been sent to the client.",
        "fr": "La facture {ref} pour {party} a été approuvée il y a {span} et n'a pas été envoyée au client."},
    # An invoice's history (#115), one line per audit event
    "history.created": {"en": "Draft created", "fr": "Brouillon créé"},
    "history.bill_recorded": {
        "en": "Supplier bill recorded as {ref}", "fr": "Facture fournisseur enregistrée sous {ref}"},
    "history.bill": {"en": "a bill", "fr": "une facture"},
    "history.updated": {"en": "Draft corrected", "fr": "Brouillon corrigé"},
    "history.submitted": {"en": "Submitted for verification", "fr": "Soumise à vérification"},
    "history.approved": {"en": "Approved", "fr": "Approuvée"},
    "history.approved_numbered": {"en": "Approved, numbered {number}", "fr": "Approuvée, numérotée {number}"},
    "history.rejected": {"en": "Rejected", "fr": "Rejetée"},
    "history.rejected_because": {"en": "Rejected: {comment}", "fr": "Rejetée : {comment}"},
    "history.sent": {"en": "Sent to the client", "fr": "Envoyée au client"},
    "history.paid": {"en": "Paid", "fr": "Payée"},
    "history.paid_on": {"en": "Paid on {date}", "fr": "Payée le {date}"},
    "history.cancelled": {"en": "Cancelled", "fr": "Annulée"},
    "history.cancelled_because": {"en": "Cancelled: {reason}", "fr": "Annulée : {reason}"},
    "history.books": {"en": "Books: {from_} to {to}", "fr": "Comptabilité : {from_} vers {to}"},
    "history.unknown_actor": {"en": "Unknown", "fr": "Inconnu"},
    "processing.pending": {"en": "Pending", "fr": "À traiter"},
    "processing.processed": {"en": "Processed", "fr": "Comptabilisée"},
    "processing.completed": {"en": "Completed", "fr": "Rapprochée"},
    "processing.archived": {"en": "Archived", "fr": "Archivée"},
    "span.day": {"en": "{n} day", "fr": "{n} jour"},
    "span.days": {"en": "{n} days", "fr": "{n} jours"},
    "party.unknown": {"en": "an unknown counterparty", "fr": "un tiers inconnu"},

    # E-mails
    "email.activation.subject": {"en": "Activate your DIXpertIA account", "fr": "Activez votre compte DIXpertIA"},
    "email.activation.body": {
        "en": "Hello {name},\n\nAn account has been created for you on DIXpertIA.\n\n"
              "Choose your password with the link below (valid for 72 hours):\n\n{link}\n\n"
              "If you were not expecting this, you can ignore this e-mail.\n\nRegards,\nDIXpertIA Team\n",
        "fr": "Bonjour {name},\n\nUn compte a été créé pour vous sur DIXpertIA.\n\n"
              "Choisissez votre mot de passe avec le lien ci-dessous (valable 72 heures) :\n\n{link}\n\n"
              "Si vous n'attendiez pas ce message, vous pouvez l'ignorer.\n\nCordialement,\nL'équipe DIXpertIA\n"},
    "email.reset.subject": {"en": "Password reset request", "fr": "Réinitialisation de votre mot de passe"},
    "email.reset.body": {
        "en": "Hello {name},\n\nYou requested a password reset for your DIXpertIA account.\n\n"
              "Click the link below to set a new password (valid for 1 hour, once):\n\n{link}\n\n"
              "If you did not request this, please ignore this email.\n\nRegards,\nDIXpertIA Team\n",
        "fr": "Bonjour {name},\n\nVous avez demandé la réinitialisation du mot de passe de votre compte DIXpertIA.\n\n"
              "Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe "
              "(valable 1 heure, une seule fois) :\n\n{link}\n\n"
              "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\n"
              "Cordialement,\nL'équipe DIXpertIA\n"},
    "email.reminder.subject": {"en": "DI Xpertia - invoice reminder", "fr": "DI Xpertia - rappel de facture"},
    "email.reminder.body": {
        "en": "{message}\n\nOpen DI Xpertia: {url}\n",
        "fr": "{message}\n\nOuvrir DI Xpertia : {url}\n"},

    # Invoice PDF
    "pdf.tagline": {
        "en": "Enterprise IT Solutions & Infrastructure Services",
        "fr": "Solutions informatiques et services d'infrastructure pour les entreprises"},
    "pdf.invoice": {"en": "INVOICE", "fr": "FACTURE"},
    "pdf.draft": {"en": "DRAFT", "fr": "BROUILLON"},
    "pdf.date": {"en": "Date", "fr": "Date"},
    "pdf.billed_to": {"en": "BILLED TO", "fr": "FACTURÉ À"},
    "pdf.due_date": {"en": "DUE DATE", "fr": "ÉCHÉANCE"},
    "pdf.status": {"en": "Status", "fr": "Statut"},
    "pdf.description": {"en": "Description", "fr": "Désignation"},
    # The public contact form (#98)
    "contact.received": {
        "en": "Thank you, your message has been sent. We will get back to you shortly.",
        "fr": "Merci, votre message a bien été envoyé. Nous revenons vers vous rapidement."},
    "contact.too_many": {
        "en": "Too many messages from you or from everyone in the last hour. Please try again later, "
              "or call us on +216 28 814 729.",
        "fr": "Trop de messages reçus dans la dernière heure. Réessayez plus tard, "
              "ou appelez-nous au +216 28 814 729."},
    "contact.not_found": {"en": "Enquiry not found", "fr": "Demande introuvable"},
    "contact.topic.security_audit": {
        "en": "Security audit / penetration testing", "fr": "Audit de sécurité / test d'intrusion"},
    "contact.topic.cloud_migration": {"en": "Hybrid cloud migration", "fr": "Migration vers le cloud hybride"},
    "contact.topic.custom_development": {
        "en": "Custom API / CRM development", "fr": "Développement sur mesure (API / CRM)"},
    "contact.topic.support_subscription": {"en": "Support subscription", "fr": "Abonnement de support"},
    "contact.topic.other": {"en": "Other request", "fr": "Autre demande"},
    "email.contact.subject": {
        "en": "Website enquiry from {name} - {topic}", "fr": "Demande du site de {name} - {topic}"},
    "email.contact.body": {
        "en": "A new enquiry arrived from the website contact form (#{id}).\n\n"
              "Name: {name}\nE-mail: {email}\nTopic: {topic}\n\n{message}\n\n"
              "Reply to this e-mail to answer {name}. All enquiries: {link}",
        "fr": "Une nouvelle demande est arrivée par le formulaire de contact du site (n° {id}).\n\n"
              "Nom : {name}\nE-mail : {email}\nSujet : {topic}\n\n{message}\n\n"
              "Répondez à cet e-mail pour répondre à {name}. Toutes les demandes : {link}"},
    "pdf.qty": {"en": "Qty", "fr": "Qté"},
    "pdf.price": {"en": "Unit price", "fr": "Prix unitaire"},
    "pdf.total": {"en": "Total", "fr": "Total"},
    # Short: the totals sit in a one-inch column, and a longer label wraps.
    "pdf.subtotal": {"en": "Subtotal", "fr": "Total HT"},
    "pdf.vat": {"en": "VAT", "fr": "TVA"},
    "pdf.grand_total": {"en": "Total due", "fr": "Total TTC"},
    "pdf.draft_note": {
        "en": "Draft - number assigned on approval", "fr": "Brouillon - numéro attribué à l'approbation"},
    "pdf.no_items": {"en": "No items.", "fr": "Aucune ligne."},
    "pdf.footer": {
        "en": "This invoice is automatically generated by DI Xpertia.<br/>"
              "For any questions, please contact billing@dixpertia.com",
        "fr": "Cette facture est générée automatiquement par DI Xpertia.<br/>"
              "Pour toute question, contactez billing@dixpertia.com"},
    "pdf.generated_on": {"en": "Generated on {date}, {time}", "fr": "Générée le {date} à {time}"},
    "pdf.status.brouillon": {"en": "Draft", "fr": "Brouillon"},
    "pdf.status.envoyee": {"en": "Sent", "fr": "Envoyée"},
    "pdf.status.payee": {"en": "Paid", "fr": "Payée"},
    "pdf.status.en_retard": {"en": "Overdue", "fr": "En retard"},
    "pdf.status.annulee": {"en": "Cancelled", "fr": "Annulée"},
}


def t(key: str, locale: str | None = None, *args, **params) -> str:
    """The catalog's text for `key`, in `locale` (default: the request's)."""
    texts = CATALOG[key]
    text = texts.get(locale or current_locale()) or texts[DEFAULT_LOCALE]
    return text.format(*args, **params) if (args or params) else text


def status_word(value, locale: str | None = None, bare: bool = False) -> str:
    """An invoice or review status inside a sentence: 'payee' -> 'paid' / 'payée'.

    `bare` names the status without an article ("draft", not "a draft").
    """
    raw = str(getattr(value, "value", value)).lower()
    if bare and f"status_bare.{raw}" in CATALOG:
        return t(f"status_bare.{raw}", locale)
    key = f"status.{raw}"
    return t(key, locale) if key in CATALOG else str(raw)


def render_notification(kind: str, params: dict | None, locale: str | None = None) -> str | None:
    """A notification's text from its kind and facts, in `locale` (default: the
    request's). None when it has no facts (written before #135) or no text."""
    key = f"notification.{kind}"
    if params is None or key not in CATALOG:
        return None
    values = dict(params)
    if "days" in values:
        days = values["days"]
        values["span"] = t("span.day" if days == 1 else "span.days", locale, n=days)
    if not values.get("party"):
        values["party"] = t("party.unknown", locale)
    if "topic" in values and f"contact.topic.{values['topic']}" in CATALOG:
        values["topic_label"] = t(f"contact.topic.{values['topic']}", locale)
    try:
        return t(key, locale, **values)
    except (KeyError, IndexError):
        return None


class ApiError(HTTPException):
    """An HTTPException whose detail is a catalog message, in the request's language.

    `code` (the catalog key) is returned alongside `detail`, so the UI and the
    tests can recognise an error without parsing its text.
    """

    def __init__(self, status_code: int, key: str, headers: dict | None = None, **params):
        super().__init__(status_code=status_code, detail=t(key, None, **params), headers=headers)
        self.code = key


# --- Dates and amounts --------------------------------------------------------------

_MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"],
}
_MONTHS_SHORT = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
}


def format_date(value: date | datetime | None, locale: str | None = None) -> str | None:
    """'Oct 17, 2026' in English, '17 oct. 2026' in French. Not the system locale:
    the server's own settings must not decide what users read."""
    if value is None:
        return None
    loc = locale or current_locale()
    month = _MONTHS_SHORT[loc][value.month - 1]
    return f"{month} {value.day:02d}, {value.year}" if loc == "en" else f"{value.day} {month} {value.year}"


def format_date_range(start: date, end: date, locale: str | None = None) -> str:
    """A leave's dates, compact: 'Mar 01 - 02, 2027' / '1 - 2 mars 2027'."""
    loc = locale or current_locale()
    if start == end:
        return format_date(start, loc)
    ms, me = _MONTHS_SHORT[loc][start.month - 1], _MONTHS_SHORT[loc][end.month - 1]
    if loc == "en":
        if (start.year, start.month) == (end.year, end.month):
            return f"{ms} {start.day:02d} - {end.day:02d}, {end.year}"
        if start.year == end.year:
            return f"{ms} {start.day:02d} - {me} {end.day:02d}, {end.year}"
        return f"{format_date(start, loc)} - {format_date(end, loc)}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day} - {end.day} {me} {end.year}"
    if start.year == end.year:
        return f"{start.day} {ms} - {end.day} {me} {end.year}"
    return f"{format_date(start, loc)} - {format_date(end, loc)}"


def format_month(value: date, locale: str | None = None) -> str:
    """'October 2026' / 'octobre 2026'."""
    loc = locale or current_locale()
    return f"{_MONTHS[loc][value.month - 1]} {value.year}"


def format_amount(value: Decimal | float | int, locale: str | None = None) -> str:
    """Tunisian dinars, three decimals: '1,234.500 TND' / '1 234,500 TND'."""
    loc = locale or current_locale()
    text = f"{Decimal(str(value)):,.3f}"
    if loc == "fr":
        # A no-break space between thousands. Not the narrow one (U+202F)
        # French typography prefers: neither PDF font has that glyph (#81).
        text = text.replace(",", " ").replace(".", ",")
    return f"{text} TND"


# --- Database rule messages ---------------------------------------------------------
# Each trigger's English format, with its % placeholders, mapped to a catalog
# key. Longest first, so "cannot go from % to % in review" wins over
# "cannot go from % to %".

_DB_FORMATS = {
    "invoice number % breaks the % series: % was expected": "db.number_breaks_named_series",
    "invoice number % breaks the series: % was expected": "db.number_breaks_series",
    "invoice % already has its legal number; it cannot change": "db.number_is_final",
    "draft % gets its legal number only when the accountant approves it": "db.number_on_approval",
    "invoice % is no longer a draft; its review is closed": "db.review_closed",
    "invoice % cannot go from % to % in review": "db.review_transition",
    "invoice % cannot be sent before the accountant approves it": "db.send_before_approval",
    "invoice % is still a draft; bookkeeping starts when it is sent": "db.books_after_sending",
    "invoice % is under review or no longer a draft and cannot be edited": "db.not_editable_in_review",
    "invoice % is no longer a draft and cannot be edited; correct it with a new document": "db.not_editable",
    "a line cannot be moved out of an invoice that is under review or no longer a draft": "db.line_move_in_review",
    "invoice % is archived and its lines are read-only; correct it with a new document in the open month":
        "db.lines_archived",
    "invoice % is under review or no longer a draft; its lines cannot be changed": "db.lines_in_review",
    "a line cannot be moved out of an invoice that is no longer a draft": "db.line_move",
    "invoice % is no longer a draft and its lines cannot be changed; correct it with a new document":
        "db.lines_not_draft",
    "the review history is append-only": "db.review_history_append_only",
    "an invoice is never approved or rejected by the person who created it": "db.no_self_review",
    "invoice % dated % would come before %, which is numbered lower but dated %. "
    "Invoice numbers must follow issue dates": "db.number_before_date",
    "invoice % dated % would come after %, which is numbered higher but dated %. "
    "Invoice numbers must follow issue dates": "db.number_after_date",
    "invoice % belongs to a closed month and cannot be deleted; issue a credit note in the open month instead":
        "db.archived_no_delete",
    "invoice % is archived; its month is closed and the processing status cannot move back":
        "db.archived_processing",
    "invoice % is archived and read-only; correct it with a new document in the open month": "db.archived_read_only",
    "invoice % is % and final": "db.status_final",
    "invoice % cannot go from % to %": "db.status_transition",
    "invoice % is waiting for verification; the accountant approves or rejects it before it can be cancelled":
        "db.cancel_under_review",
    "invoice % belongs to a closed month and cannot be cancelled; correct it with a credit note in the open month":
        "db.cancel_closed_month",
    "invoice % cannot be paid on %, a date in the future": "db.paid_in_future",
    "the accounting period % is closed; an invoice cannot be dated into it. Issue it in the open month instead":
        "db.period_closed",
    "invoice % cannot be deleted: its number is part of a gapless series. Cancel it instead (statut ANNULEE), "
    "which keeps the row and the number": "db.never_deleted",
    "audit event % cannot be changed or deleted: the audit trail is append-only": "db.audit_append_only",
    "An employee cannot validate their own leave request": "db.leave_self_validation",
}


def _pattern(fmt: str) -> re.Pattern:
    return re.compile("^" + "(.*?)".join(re.escape(p) for p in fmt.split("%")) + "$")


DB_PATTERNS = sorted(((_pattern(f), k, f) for f, k in _DB_FORMATS.items()), key=lambda p: -len(p[2]))


def translate_db_message(message: str, locale: str | None = None) -> str | None:
    """A trigger's English message in `locale`, or None if it is not one of ours.

    Statuses inside the message ('payee', 'SUBMITTED') are translated too.
    """
    for pattern, key, _ in DB_PATTERNS:
        match = pattern.match(message.strip())
        if match:
            # A transition names its two statuses; other messages describe one.
            bare = key in ("db.status_transition", "db.review_transition")
            args = [status_word(a, locale, bare) if f"status.{a.lower()}" in CATALOG else a
                    for a in match.groups()]
            return t(key, locale, *args)
    return None
