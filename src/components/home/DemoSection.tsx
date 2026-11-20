import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import type { DemoProvider, DemoService, PublicDemo } from '../../api';
import { useLocale, useT, type MessageKey } from '../../i18n';
import { LogoMark } from './LogoMark';
import { Reveal } from './motion';
import { SectionHeading } from './Services';

const SERVICE: Record<DemoService, MessageKey> = {
  cloud: 'demos.service.cloud',
  security: 'demos.service.security',
  software: 'demos.service.software',
};

const PROVIDER: Record<DemoProvider, MessageKey> = {
  drive: 'demos.provider.drive',
  youtube: 'demos.provider.youtube',
  vimeo: 'demos.provider.vimeo',
};

/**
 * "02 — Demo" (#234, design/demo-videos/README.md, part 2): the published
 * demos as our own cards. Nothing is sent to Google, YouTube or Vimeo before
 * Play: the preview images come from our domain, and the player's iframe
 * exists only while the lightbox is open. The page renders this section only
 * when at least one demo is published.
 */
export default function DemoSection({ demos }: { demos: PublicDemo[] }) {
  const t = useT();
  const [playing, setPlaying] = useState<PublicDemo | null>(null);
  // The Play button that opened the player, to give focus back on close.
  const opener = useRef<HTMLButtonElement | null>(null);

  const close = () => {
    setPlaying(null);
    // After the lightbox has left the page, so focus lands on the card.
    requestAnimationFrame(() => opener.current?.focus());
  };

  return (
    <section id="demo" aria-labelledby="demo-title" className="scroll-mt-[68px] border-t border-home-fg/10 bg-home-bg">
      <div className="mx-auto flex max-w-[1312px] flex-col gap-[clamp(32px,4vw,48px)] px-[clamp(20px,5vw,48px)] py-[clamp(72px,9vw,128px)]">
        <SectionHeading
          eyebrow={t('home.demo.eyebrow')}
          title={t('home.demo.title')}
          id="demo-title"
          note={t('home.demo.note')}
        />
        <ul className="m-0 grid list-none grid-cols-[repeat(auto-fill,minmax(min(100%,340px),1fr))] gap-x-[clamp(20px,2vw,28px)] gap-y-[clamp(28px,3vw,40px)] border-t border-home-fg p-0 pt-[clamp(24px,3vw,36px)]">
          {demos.map((demo, i) => (
            <Reveal as="li" key={demo.id} index={Math.min(i, 3) + 1} className="min-w-0">
              <DemoCard
                demo={demo}
                onPlay={(button) => {
                  opener.current = button;
                  setPlaying(demo);
                }}
              />
            </Reveal>
          ))}
        </ul>
      </div>
      {playing && <Player demo={playing} onClose={close} />}
    </section>
  );
}

function useDemoText(demo: PublicDemo) {
  const locale = useLocale();
  return locale === 'fr'
    ? { title: demo.title_fr, description: demo.description_fr }
    : { title: demo.title_en, description: demo.description_en };
}

function DemoCard({ demo, onPlay }: { demo: PublicDemo; onPlay: (button: HTMLButtonElement) => void }) {
  const t = useT();
  const { title, description } = useDemoText(demo);
  const [failed, setFailed] = useState(false);
  const showImage = demo.preview_image && !failed;

  return (
    <article className="flex flex-col gap-[18px]">
      <button
        type="button"
        aria-label={t('home.demo.play', { title })}
        aria-haspopup="dialog"
        onClick={(e) => onPlay(e.currentTarget)}
        className="relative block aspect-video w-full cursor-pointer overflow-hidden rounded-xl text-left transition-shadow duration-300 hover:shadow-xl hover:ring-1 hover:ring-home-fg"
      >
        {showImage ? (
          <img
            src={demo.preview_image!}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setFailed(true)}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          // The branded fallback: no image was stored, or it did not load.
          // The content sits in the upper 80% so the Play button never covers it.
          <span aria-hidden="true" className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-xl border border-home-fg/12 bg-home-surface pb-[20%] text-home-fg">
            <LogoMark className="h-[41px] w-[56px]" />
            <span className="font-mono text-[10px] leading-none font-medium tracking-[0.16em] text-home-fg/62">{t('home.demo.fallback')}</span>
          </span>
        )}
        <span aria-hidden="true" className="absolute bottom-[18px] left-[18px] flex h-[60px] w-[60px] items-center justify-center rounded-full bg-lime text-ink shadow-lg ring-1 ring-ink/14 ring-inset">
          <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M8 5v14l11-7z" fill="currentColor" />
          </svg>
        </span>
      </button>
      <div className="flex flex-col gap-2.5">
        {demo.service && (
          <span className="font-mono text-home-meta font-medium tracking-[0.14em] text-home-accent-text uppercase">{t(SERVICE[demo.service])}</span>
        )}
        <h3 className="m-0 text-[clamp(20px,1.7vw,24px)] leading-[1.22] font-semibold tracking-[-0.015em] text-balance">{title}</h3>
        <p className="m-0 line-clamp-3 text-[15px] leading-[1.6] text-pretty text-home-fg/72">{description}</p>
      </div>
    </article>
  );
}

/**
 * The lightbox: a native modal <dialog>, so Tab stays inside and the rest of
 * the page is inert. Esc, the close button or a click on the backdrop close
 * it. The iframe is created here and destroyed with it.
 */
function Player({ demo, onClose }: { demo: PublicDemo; onClose: () => void }) {
  const t = useT();
  const { title } = useDemoText(demo);
  const dialog = useRef<HTMLDialogElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    el.showModal();
    closeButton.current?.focus();
    // The page does not scroll behind the player.
    const root = document.documentElement;
    const before = root.style.overflow;
    root.style.overflow = 'hidden';
    return () => {
      root.style.overflow = before;
      if (el.open) el.close();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      aria-labelledby="demo-player-title"
      onCancel={(e) => {
        // Esc: closed by React state, so the iframe goes with it.
        e.preventDefault();
        onClose();
      }}
      className="m-0 h-full max-h-none w-full max-w-none bg-transparent p-0 text-paper backdrop:bg-home-player-scrim"
    >
      <div
        className="flex h-full w-full items-center justify-center p-3 sm:p-12"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose();
        }}
      >
        <div className="flex max-h-full w-full max-w-[1080px] flex-col gap-3.5 overflow-auto rounded-2xl border border-home-player-line bg-home-player p-[clamp(14px,2vw,22px)] shadow-2xl">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 flex-1 flex-col gap-2 pt-1">
              {demo.service && (
                <span className="font-mono text-home-meta font-medium tracking-[0.14em] text-lime uppercase">{t(SERVICE[demo.service])}</span>
              )}
              <h2 id="demo-player-title" className="m-0 text-[clamp(18px,1.8vw,24px)] leading-[1.25] font-semibold tracking-[-0.015em]">
                {title}
              </h2>
            </div>
            <button
              ref={closeButton}
              type="button"
              onClick={onClose}
              aria-label={t('home.demo.close')}
              className="flex h-11 w-11 flex-none cursor-pointer items-center justify-center rounded-full border border-paper/28 text-paper transition-colors hover:bg-paper/10"
            >
              <X className="h-[18px] w-[18px]" aria-hidden="true" />
            </button>
          </div>
          <div className="relative aspect-video flex-none overflow-hidden rounded-[10px] bg-ink">
            <iframe
              src={demo.embed_url}
              title={t('home.demo.player', { title })}
              allow="autoplay; fullscreen; picture-in-picture"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
              className="absolute inset-0 h-full w-full border-0"
            />
          </div>
          <div className="flex justify-between gap-3 px-1 pb-0.5 font-mono text-xs leading-[1.4] font-medium whitespace-nowrap text-paper/72">
            <span>{t('home.demo.via', { provider: t(PROVIDER[demo.provider]) })}</span>
            <span aria-hidden="true" className="hidden sm:inline">{t('home.demo.esc')}</span>
          </div>
        </div>
      </div>
    </dialog>
  );
}
