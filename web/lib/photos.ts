export interface Photo {
  url: string;
  author: string;
  license: string;
  page: string;
}

type Point = [number, number];
type Store = Pick<Storage, "getItem" | "setItem">;
type Page = {
  title: string;
  index?: number;
  pageimage?: string;
  coordinates?: { lat: number; lon: number }[];
};

const WIKIPEDIA = "https://es.wikipedia.org/w/api.php";
const COMMONS = "https://commons.wikimedia.org/w/api.php";
const MAX_KM = 25;
const NOT_PHOTO = /\.svg$|mapa|map|localizaci|location|escudo|bandera|flag|coat|logo/i;
const memory = new Map<string, Photo>();

export function isPhotoFile(name: string): boolean {
  return !NOT_PHOTO.test(name);
}

export function plainText(html: string): string {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .trim();
}

// null means no photo was found; network and HTTP failures reject so the caller can log them.
export async function destinationPhoto(
  place: string,
  point: Point,
  fetcher: typeof fetch = fetch,
  storage?: Store,
): Promise<Photo | null> {
  const store = storage ?? browserStorage();
  const key = `photo:${point[0].toFixed(3)},${point[1].toFixed(3)}`;
  const cached = memory.get(key) ?? readStored(store, key);
  if (cached) return cached;

  const file =
    (await byTitle(place, point, fetcher)) ??
    (await byTitle(`${place} (Perú)`, point, fetcher)) ??
    (await nearest(point, fetcher));
  if (!file) return null;

  const photo = await credit(file, fetcher);
  memory.set(key, photo);
  try {
    store?.setItem(key, JSON.stringify(photo));
  } catch {
    // Private windows throw on write; the in-memory copy still serves this visit.
  }
  return photo;
}

// Reading window.localStorage itself throws a SecurityError when site data is blocked.
function browserStorage(): Store | undefined {
  try {
    return globalThis.localStorage;
  } catch {
    return undefined;
  }
}

function readStored(storage: Store | undefined, key: string): Photo | null {
  try {
    const raw = storage?.getItem(key);
    return raw ? (JSON.parse(raw) as Photo) : null;
  } catch {
    return null;
  }
}

async function query(base: string, params: Record<string, string>, fetcher: typeof fetch): Promise<{ pages: Record<string, unknown> }> {
  const search = new URLSearchParams({ action: "query", format: "json", origin: "*", ...params });
  const response = await fetcher(`${base}?${search}`);
  if (!response.ok) throw new Error(`Wikipedia HTTP ${response.status}`);
  const body = (await response.json()) as { query?: { pages?: Record<string, unknown> } };
  return { pages: body.query?.pages ?? {} };
}

// A same-name article can belong to another country, so only coordinates near the stop count.
async function byTitle(title: string, point: Point, fetcher: typeof fetch): Promise<string | null> {
  const { pages } = await query(
    WIKIPEDIA,
    { titles: title, redirects: "1", prop: "pageimages|coordinates", piprop: "name" },
    fetcher,
  );
  const page = Object.values(pages)[0] as Page | undefined;
  const coords = page?.coordinates?.[0];
  if (!page?.pageimage || !coords || !isPhotoFile(page.pageimage)) return null;
  return km(point, [coords.lat, coords.lon]) < MAX_KM ? page.pageimage : null;
}

async function nearest(point: Point, fetcher: typeof fetch): Promise<string | null> {
  const { pages } = await query(
    WIKIPEDIA,
    {
      generator: "geosearch",
      ggscoord: `${point[0]}|${point[1]}`,
      ggsradius: "10000",
      ggslimit: "20",
      prop: "pageimages",
      piprop: "name",
    },
    fetcher,
  );
  const sorted = (Object.values(pages) as Page[]).sort((a, b) => (a.index ?? 99) - (b.index ?? 99));
  return sorted.find((page) => page.pageimage && isPhotoFile(page.pageimage))?.pageimage ?? null;
}

async function credit(file: string, fetcher: typeof fetch): Promise<Photo> {
  const { pages } = await query(
    COMMONS,
    { titles: `File:${file}`, prop: "imageinfo", iiprop: "url|extmetadata", iiurlwidth: "1280" },
    fetcher,
  );
  const info = (Object.values(pages)[0] as { imageinfo?: { thumburl?: string; extmetadata?: Record<string, { value?: string }> }[] })
    ?.imageinfo?.[0];
  if (!info?.thumburl) throw new Error(`Commons has no thumbnail for ${file}`);
  return {
    url: info.thumburl,
    author: plainText(info.extmetadata?.Artist?.value ?? "") || "Wikimedia Commons",
    license: info.extmetadata?.LicenseShortName?.value ?? "Wikimedia Commons",
    page: `https://commons.wikimedia.org/wiki/File:${file}`,
  };
}

function km(a: Point, b: Point): number {
  return 111 * Math.hypot(a[0] - b[0], (a[1] - b[1]) * Math.cos((a[0] * Math.PI) / 180));
}
