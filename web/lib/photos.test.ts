import { expect, test, vi } from "vitest";
import { destinationPhoto, isPhotoFile, plainText } from "./photos";

type Article = { title: string; lat?: number; lon?: number; image?: string };

function json(body: unknown) {
  return new Response(JSON.stringify(body));
}

function commons(url: URL) {
  const file = url.searchParams.get("titles")!.replace("File:", "");
  return json({
    query: {
      pages: {
        "1": {
          imageinfo: [
            {
              thumburl: `https://upload.wikimedia.org/thumb/${file}/1280px-${file}`,
              extmetadata: {
                Artist: { value: '<a href="//commons.wikimedia.org/wiki/User:Elemaki">Elemaki</a>' },
                LicenseShortName: { value: "CC BY-SA 2.5" },
              },
            },
          ],
        },
      },
    },
  });
}

// Routes like the real endpoints: Commons by host, articles by title, nearest pages by generator.
function wiki(articles: Record<string, Article>, nearby: { index: number; pageimage?: string }[] = []) {
  return vi.fn<typeof fetch>(async (input) => {
    const url = new URL(String(input));
    if (url.host === "commons.wikimedia.org") return commons(url);
    if (url.searchParams.get("generator") === "geosearch") {
      const pages = Object.fromEntries(nearby.map((page, i) => [String(i + 1), { title: `P${i}`, ...page }]));
      return json({ query: { pages } });
    }
    const article = articles[url.searchParams.get("titles")!];
    if (!article) return json({ query: { pages: { "-1": { title: "?", missing: "" } } } });
    return json({
      query: {
        pages: {
          "7": {
            title: article.title,
            pageimage: article.image,
            coordinates: article.lat === undefined ? undefined : [{ lat: article.lat, lon: article.lon }],
          },
        },
      },
    });
  });
}

const memory = () => {
  const data = new Map<string, string>();
  return { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) };
};

test("finds the photo by exact title when the article sits within 25 km", async () => {
  const fetcher = wiki({ "Kuélap": { title: "Kuélap", lat: -6.42, lon: -77.95, image: "Arquitectura_de_Kuelap.jpg" } });

  const photo = await destinationPhoto("Kuélap", [-6.42, -77.92], fetcher, memory());

  expect(photo).toEqual({
    url: "https://upload.wikimedia.org/thumb/Arquitectura_de_Kuelap.jpg/1280px-Arquitectura_de_Kuelap.jpg",
    author: "Elemaki",
    license: "CC BY-SA 2.5",
    page: "https://commons.wikimedia.org/wiki/File:Arquitectura_de_Kuelap.jpg",
  });
  expect(String(fetcher.mock.calls[0][0])).toContain("titles=Ku%C3%A9lap");
});

test('rejects a same-name article far away and tries "<name> (Perú)"', async () => {
  const fetcher = wiki({
    Sauce: { title: "Sauce", lat: 40.4, lon: -3.7, image: "Madrid.jpg" },
    "Sauce (Perú)": { title: "Sauce (Perú)", lat: -6.69, lon: -76.22, image: "Laguna_Azul.jpg" },
  });

  const photo = await destinationPhoto("Sauce", [-6.69, -76.22], fetcher, memory());

  expect(photo?.url).toContain("Laguna_Azul.jpg");
});

test("falls back to the nearest geosearch page whose image is a photo", async () => {
  const fetcher = wiki({}, [
    { index: 2, pageimage: "Laguna.jpg" },
    { index: 1, pageimage: "Peru_physical_map.svg" },
  ]);

  const photo = await destinationPhoto("Huacachina", [-14.09, -75.76], fetcher, memory());

  expect(photo?.url).toContain("Laguna.jpg");
});

test("returns null when nothing nearby has a photo", async () => {
  const fetcher = wiki({}, [{ index: 1, pageimage: "Escudo_de_Ica.png" }, { index: 2 }]);

  expect(await destinationPhoto("Nauta", [-4.51, -73.58], fetcher, memory())).toBeNull();
});

test("rejects on an HTTP error", async () => {
  const fetcher = vi.fn<typeof fetch>(async () => new Response("busy", { status: 503 }));

  await expect(destinationPhoto("Pucallpa", [-8.38, -74.55], fetcher, memory())).rejects.toThrow("503");
});

test.each([
  ["Kuelap.jpg", true],
  ["Mapa_de_localización_Puno.svg", false],
  ["Escudo_de_Ica.png", false],
  ["Bandera.jpg", false],
])("isPhotoFile(%s) is %s", (name, expected) => {
  expect(isPhotoFile(name)).toBe(expected);
});

test("strips tags and decodes entities", () => {
  expect(plainText('<a href="x">Elemaki</a> &amp; co')).toBe("Elemaki & co");
});

test("serves a cached photo without fetching and survives a storage that throws", async () => {
  const articles = { "Kuélap": { title: "Kuélap", lat: -6.5, lon: -77.5, image: "K.jpg" } };
  const storage = memory();
  const first = await destinationPhoto("Kuélap", [-6.5001, -77.5001], wiki(articles), storage);
  const fetcher = wiki(articles);

  const second = await destinationPhoto("Kuélap", [-6.5001, -77.5001], fetcher, storage);

  expect(second).toEqual(first);
  expect(fetcher).not.toHaveBeenCalled();

  const broken = {
    getItem: () => {
      throw new Error("denied");
    },
    setItem: () => {
      throw new Error("denied");
    },
  };
  const other = wiki({ Tarapoto: { title: "Tarapoto", lat: -6.49, lon: -76.36, image: "T.jpg" } });
  expect((await destinationPhoto("Tarapoto", [-6.49, -76.36], other, broken))?.url).toContain("T.jpg");
});
