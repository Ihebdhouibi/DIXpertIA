import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// send() is tested without a browser: the translations module reads window and
// document as it loads, so it is replaced by a key-for-text stand-in.
vi.mock('./i18n', () => ({ getLocale: () => 'en', t: (key: string) => key }));

/** localStorage as every tab of one browser shares it. */
class SharedStorage {
  private items = new Map<string, string>();
  getItem(key: string) {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.items.set(key, value);
  }
  removeItem(key: string) {
    this.items.delete(key);
  }
}

let storage: SharedStorage;

/** api.ts as a tab loads it, with `token` already stored. */
async function tabWithToken(token: string) {
  storage.setItem('token', token);
  vi.resetModules();
  return import('./api');
}

beforeEach(() => {
  storage = new SharedStorage();
  vi.stubGlobal('localStorage', storage);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// A session changed in another tab (#238).
describe('a 401 and the token shared by the tabs', () => {
  it('removes an expired token for every tab', async () => {
    const api = await tabWithToken('old');
    const unauthorized = vi.fn();
    api.setUnauthorizedHandler(unauthorized);
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 401 })));

    await expect(api.auth.me()).rejects.toMatchObject({ status: 401, message: 'common.sessionExpired' });
    expect(storage.getItem('token')).toBeNull();
    expect(api.getToken()).toBeNull();
    expect(unauthorized).toHaveBeenCalledOnce();
  });

  it("keeps a newer token another tab stored while the request was in flight", async () => {
    const api = await tabWithToken('old');
    const unauthorized = vi.fn();
    api.setUnauthorizedHandler(unauthorized);
    // The request leaves with "old"; before its answer, another tab changes
    // the password, which revokes "old" and stores a fresh token.
    vi.stubGlobal('fetch', vi.fn(async () => {
      storage.setItem('token', 'fresh');
      return new Response(null, { status: 401 });
    }));

    await expect(api.auth.me()).rejects.toMatchObject({ status: 401, message: 'common.sessionChangedElsewhere' });
    expect(storage.getItem('token')).toBe('fresh');
    expect(api.getToken()).toBeNull();
    expect(unauthorized).toHaveBeenCalledOnce();
  });
});

describe('a request after another tab changed the session', () => {
  it('is not sent with a token this tab does not show', async () => {
    const api = await tabWithToken('admin');
    const changed = vi.fn();
    api.setSessionChangedHandler(changed);
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);
    storage.setItem('token', 'accountant');

    await expect(api.auth.me()).rejects.toMatchObject({ status: 401, message: 'common.sessionChangedElsewhere' });
    expect(fetch).not.toHaveBeenCalled();
    expect(changed).toHaveBeenCalledOnce();
  });

  it('carries this tab\'s token when nothing changed', async () => {
    const api = await tabWithToken('admin');
    const fetch = vi.fn(async (_path: string, _init: RequestInit) => new Response(JSON.stringify({ id: 'USR-001' }), { status: 200 }));
    vi.stubGlobal('fetch', fetch);

    await expect(api.auth.me()).resolves.toMatchObject({ id: 'USR-001' });
    const headers = fetch.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer admin');
  });
});
