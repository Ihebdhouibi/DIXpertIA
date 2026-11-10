import { defineMessages } from '../define';

/**
 * demos: the admin's demo videos screen (#233), copy from the design handoff
 * (design/demo-videos/README.md). See ../define.ts; keys start with "demos.".
 */
export default defineMessages('demos', {
  // Page
  'demos.title': { fr: 'Démos', en: 'Demos' },
  'demos.intro': {
    fr: 'Les vidéos affichées dans la section Démo du site web.',
    en: 'The videos shown in the Demo section of the website.',
  },
  'demos.new': { fr: 'Nouvelle démo', en: 'New demo' },
  'demos.caption': { fr: "Démos, dans l'ordre d'affichage du site", en: 'Demos, in website display order' },
  'demos.loading': { fr: 'Chargement des démos…', en: 'Loading demos…' },
  'demos.couldNotLoad': { fr: 'Impossible de charger les démos.', en: "Couldn't load the demos." },
  'demos.retry': { fr: 'Réessayer', en: 'Try again' },
  'demos.count': {
    fr: { one: '{count} démo', other: '{count} démos' },
    en: { one: '{count} demo', other: '{count} demos' },
  },
  'demos.onSite': {
    fr: { one: '{count} sur le site', other: '{count} sur le site' },
    en: { one: '{count} on the website', other: '{count} on the website' },
  },

  // Columns
  'demos.col.order': { fr: 'Ordre', en: 'Order' },
  'demos.col.preview': { fr: 'Aperçu', en: 'Preview' },
  'demos.col.title': { fr: 'Titre', en: 'Title' },
  'demos.col.service': { fr: 'Service', en: 'Service' },
  'demos.col.status': { fr: 'Statut', en: 'Status' },
  'demos.col.actions': { fr: 'Actions', en: 'Actions' },

  // Values
  'demos.provider.drive': { fr: 'Google Drive', en: 'Google Drive' },
  'demos.provider.youtube': { fr: 'YouTube', en: 'YouTube' },
  'demos.provider.vimeo': { fr: 'Vimeo', en: 'Vimeo' },
  'demos.service.cloud': { fr: 'Cloud', en: 'Cloud' },
  'demos.service.security': { fr: 'Cybersécurité', en: 'Cybersecurity' },
  'demos.service.software': { fr: 'Logiciel sur mesure', en: 'Custom software' },
  'demos.service.none': { fr: 'Aucun service', en: 'No service' },
  'demos.published': { fr: 'Publiée', en: 'Published' },
  'demos.hidden': { fr: 'Masquée', en: 'Hidden' },
  'demos.auto': { fr: 'Auto', en: 'Auto' },
  'demos.autoLabel': { fr: 'Miniature automatique', en: 'Automatic thumbnail' },

  // Row actions: every name carries the title.
  'demos.moveUp': { fr: 'Monter : {title}', en: 'Move up: {title}' },
  'demos.moveDown': { fr: 'Descendre : {title}', en: 'Move down: {title}' },
  'demos.edit': { fr: 'Modifier', en: 'Edit' },
  'demos.editLabel': { fr: 'Modifier : {title}', en: 'Edit: {title}' },
  'demos.hide': { fr: 'Masquer', en: 'Hide' },
  'demos.hideLabel': { fr: 'Masquer : {title}', en: 'Hide: {title}' },
  'demos.publish': { fr: 'Publier', en: 'Publish' },
  'demos.publishLabel': { fr: 'Publier : {title}', en: 'Publish: {title}' },
  'demos.delete': { fr: 'Supprimer', en: 'Delete' },
  'demos.deleteLabel': { fr: 'Supprimer : {title}', en: 'Delete: {title}' },
  'demos.position': { fr: 'Position {position}', en: 'Position {position}' },
  'demos.moved': {
    fr: '{title} déplacée en position {position} sur {count}.',
    en: '{title} moved to position {position} of {count}.',
  },
  'demos.couldNotMove': {
    fr: "Impossible de changer l'ordre. L'ordre précédent est rétabli.",
    en: "Couldn't change the order. The previous order is back.",
  },
  'demos.nowPublished': { fr: 'Démo « {title} » publiée.', en: 'Demo "{title}" published.' },
  'demos.nowHidden': { fr: 'Démo « {title} » masquée.', en: 'Demo "{title}" hidden.' },
  'demos.couldNotUpdate': { fr: 'Impossible de modifier la démo.', en: "Couldn't update the demo." },

  // Delete
  'demos.deleteTitle': { fr: 'Supprimer cette démo ?', en: 'Delete this demo?' },
  'demos.deleteMessage': {
    fr: '« {title} » disparaît du site web. La vidéo elle-même reste chez son hébergeur.',
    en: '"{title}" disappears from the website. The video itself stays with its host.',
  },
  'demos.deleted': { fr: 'Démo supprimée.', en: 'Demo deleted.' },
  'demos.couldNotDelete': { fr: 'Impossible de supprimer la démo.', en: "Couldn't delete the demo." },

  // Empty state
  'demos.emptyTitle': { fr: "Aucune démo pour l'instant", en: 'No demos yet' },
  'demos.emptyMessage': {
    fr: "Collez le lien d'une vidéo hébergée sur Google Drive, YouTube ou Vimeo pour ajouter votre première démo. Une fois publiée, elle apparaît dans la section Démo du site.",
    en: 'Paste a link to a video hosted on Google Drive, YouTube or Vimeo to add your first demo. Once published, it appears in the Demo section of the website.',
  },
  'demos.emptyAction': { fr: 'Ajouter la première démo', en: 'Add the first demo' },
  'demos.emptyNote': {
    fr: "La section Démo reste absente du site tant qu'aucune démo n'est publiée.",
    en: 'The Demo section stays off the website until a demo is published.',
  },

  // Form
  'demos.form.addTitle': { fr: 'Nouvelle démo', en: 'New demo' },
  'demos.form.editTitle': { fr: 'Modifier la démo', en: 'Edit demo' },
  'demos.form.optional': { fr: 'Facultatif', en: 'Optional' },
  'demos.form.link': { fr: 'Lien de la vidéo', en: 'Video link' },
  'demos.form.linkHint': {
    fr: "Collez le lien de partage d'une vidéo Google Drive, YouTube ou Vimeo.",
    en: 'Paste the share link of a Google Drive, YouTube or Vimeo video.',
  },
  'demos.form.linkRequired': { fr: 'Collez le lien de la vidéo.', en: 'Paste the video link.' },
  'demos.form.linkUnknown': {
    fr: 'Lien non reconnu. Collez un lien de partage Google Drive (drive.google.com/file/d/…), YouTube ou Vimeo.',
    en: "We don't recognise this link. Paste a Google Drive (drive.google.com/file/d/…), YouTube or Vimeo share link.",
  },
  'demos.form.source': { fr: 'Source : {source}', en: 'Source: {source}' },
  'demos.form.previewQuestion': { fr: 'Est-ce la bonne vidéo ?', en: 'Is this the right video?' },
  'demos.form.previewNote': {
    fr: "Aperçu visible par vous seul : les visiteurs voient notre propre carte jusqu'à ce qu'ils lancent la lecture.",
    en: 'Preview for you only: visitors see our own card until they press Play.',
  },
  'demos.form.playerTitle': { fr: 'Vidéo : {title}', en: 'Video: {title}' },
  'demos.form.image': { fr: "Lien de l'image d'aperçu", en: 'Preview image link' },
  'demos.form.imageAuto': {
    fr: 'La miniature automatique de la vidéo sera utilisée.',
    en: "The video's automatic thumbnail will be used.",
  },
  'demos.form.imageAutoHint': {
    fr: "Sa qualité n'est pas garantie ; une image 1280 × 720 donne le meilleur rendu.",
    en: "Its quality isn't guaranteed; a 1280 × 720 image looks best.",
  },
  'demos.form.imageHint': {
    fr: "Un lien de partage d'image Google Drive. L'image est récupérée à l'enregistrement.",
    en: 'A Google Drive image share link. The image is fetched when you save.',
  },
  'demos.form.imageUnknown': {
    fr: "L'image d'aperçu doit être un lien Google Drive (drive.google.com/file/d/…).",
    en: 'The preview image must be a Google Drive link (drive.google.com/file/d/…).',
  },
  'demos.form.content': { fr: 'Contenu', en: 'Content' },
  'demos.form.lang.fr': { fr: 'Français', en: 'Français' },
  'demos.form.lang.en': { fr: 'English', en: 'English' },
  'demos.form.complete': { fr: 'Complet', en: 'Complete' },
  'demos.form.missing': { fr: 'Manquant', en: 'Missing' },
  'demos.form.titleLabel': { fr: 'Titre · {lang}', en: 'Title · {lang}' },
  'demos.form.descriptionLabel': { fr: 'Description · {lang}', en: 'Description · {lang}' },
  'demos.form.counter': { fr: '{count} / {max}', en: '{count} / {max}' },
  'demos.form.languagesHint': {
    fr: 'Les deux langues sont obligatoires : le site affiche à chaque visiteur sa langue.',
    en: 'Both languages are required: the website shows each visitor their language.',
  },
  'demos.form.titleMissing.fr': { fr: 'Ajoutez le titre en français.', en: 'Add the French title.' },
  'demos.form.titleMissing.en': { fr: 'Ajoutez le titre en anglais.', en: 'Add the English title.' },
  'demos.form.descriptionMissing.fr': { fr: 'Ajoutez la description en français.', en: 'Add the French description.' },
  'demos.form.descriptionMissing.en': { fr: 'Ajoutez la description en anglais.', en: 'Add the English description.' },
  'demos.form.service': { fr: 'Service', en: 'Service' },
  'demos.form.status': { fr: 'Statut', en: 'Status' },
  'demos.form.statusHint': {
    fr: 'Les démos masquées ne sont pas affichées sur le site.',
    en: 'Hidden demos are not shown on the website.',
  },
  'demos.form.attention': {
    fr: {
      one: "{count} champ demande votre attention avant l'enregistrement.",
      other: "{count} champs demandent votre attention avant l'enregistrement.",
    },
    en: { one: '{count} field needs attention before saving.', other: '{count} fields need attention before saving.' },
  },
  'demos.form.cancel': { fr: 'Annuler', en: 'Cancel' },
  'demos.form.save': { fr: 'Enregistrer', en: 'Save' },
  'demos.form.couldNotSave': {
    fr: "Impossible d'enregistrer la démo. Vérifiez votre connexion et réessayez : rien n'est perdu.",
    en: "Couldn't save the demo. Check your connection and try again: nothing was lost.",
  },
  'demos.form.saved': { fr: 'Démo « {title} » enregistrée.', en: 'Demo "{title}" saved.' },
});
