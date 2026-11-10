import type { DemoProvider } from './api';

/**
 * Recognise a demo's video link while the admin types it (#233). The same
 * rules as the server's app/services/demo_links.py, which stays the
 * authority: this copy only lets the form name the source and show the
 * player before saving. Keep the two in step.
 */

export interface VideoLink {
  provider: DemoProvider;
  videoId: string;
}

const DRIVE_ID = '[A-Za-z0-9_-]{10,100}';
const YOUTUBE_ID = '[A-Za-z0-9_-]{11}';
const DRIVE_HOSTS = new Set(['drive.google.com', 'docs.google.com']);
const YOUTUBE_HOSTS = new Set([
  'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com',
]);
const VIMEO_HOSTS = new Set(['vimeo.com', 'www.vimeo.com', 'player.vimeo.com']);

const whole = (pattern: string) => new RegExp(`^${pattern}$`);

function parse(url: string): URL | null {
  try {
    const parsed = new URL(url.trim());
    return parsed.protocol === 'https:' ? parsed : null;
  } catch {
    return null;
  }
}

function driveId(url: URL): string | null {
  const match = url.pathname.match(whole(`/file/d/(${DRIVE_ID})(?:/[^/]*)?/?`));
  if (match) return match[1];
  if (['/open', '/uc', '/thumbnail'].includes(url.pathname)) {
    const id = url.searchParams.get('id') ?? '';
    if (whole(DRIVE_ID).test(id)) return id;
  }
  return null;
}

/** The provider and video id of a Drive, YouTube or Vimeo link, or null. */
export function parseVideoLink(text: string): VideoLink | null {
  const url = parse(text);
  if (!url) return null;
  const host = url.hostname.toLowerCase();
  if (DRIVE_HOSTS.has(host)) {
    const id = driveId(url);
    return id ? { provider: 'drive', videoId: id } : null;
  }
  if (host === 'youtu.be') {
    const match = url.pathname.match(whole(`/(${YOUTUBE_ID})/?`));
    return match ? { provider: 'youtube', videoId: match[1] } : null;
  }
  if (YOUTUBE_HOSTS.has(host)) {
    if (url.pathname === '/watch') {
      const id = url.searchParams.get('v') ?? '';
      return whole(YOUTUBE_ID).test(id) ? { provider: 'youtube', videoId: id } : null;
    }
    const match = url.pathname.match(whole(`/(?:embed|shorts|live)/(${YOUTUBE_ID})/?`));
    return match ? { provider: 'youtube', videoId: match[1] } : null;
  }
  if (VIMEO_HOSTS.has(host)) {
    // An unlisted video carries a hash: vimeo.com/123/abc or ?h=abc.
    const match = url.pathname.match(/^\/(?:video\/)?(\d{1,12})(?:\/([0-9a-f]{6,20}))?\/?$/);
    if (!match) return null;
    const unlisted = match[2] || url.searchParams.get('h') || '';
    if (unlisted && !/^[0-9a-f]{6,20}$/.test(unlisted)) return null;
    return { provider: 'vimeo', videoId: unlisted ? `${match[1]}-${unlisted}` : match[1] };
  }
  return null;
}

/** Whether a preview image link is a Drive file link: the only source accepted for now. */
export function isDriveImage(text: string): boolean {
  const url = parse(text);
  return url !== null && DRIVE_HOSTS.has(url.hostname.toLowerCase()) && driveId(url) !== null;
}

/** The player to frame, as the server builds it: YouTube's no-cookie host, Vimeo's do-not-track flag. */
export function embedUrl({ provider, videoId }: VideoLink): string {
  if (provider === 'drive') return `https://drive.google.com/file/d/${videoId}/preview`;
  if (provider === 'youtube') return `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`;
  const [number, unlisted] = videoId.split('-');
  return `https://player.vimeo.com/video/${number}?dnt=1${unlisted ? `&h=${unlisted}` : ''}`;
}
