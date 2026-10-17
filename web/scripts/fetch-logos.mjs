// Downloads the logos of operators and ticket sites once, so the web serves them itself and never
// depends on a third party at view time. Re-run after adding a domain: `node scripts/fetch-logos.mjs`.
// A domain with no logo is skipped; the page shows the operator's initials instead.
import { mkdir, writeFile } from "node:fs/promises";

const DOMAINS = [
  // operators, matching OPERATOR_SITES in lib/format.ts
  "latamairlines.com",
  "skyairline.com",
  "jetsmart.com",
  "starperu.com",
  "cruzdelsur.com.pe",
  "oltursa.pe",
  "civa.com.pe",
  "movilbus.pe",
  "perurail.com",
  "incarail.com",
  // sites the searches read from
  "redbus.pe",
  "kupos.pe",
  "checkmybus.pe",
  "buscobus.pe",
  "busbud.com",
  "kayak.com.pe",
  "jetcost.com.pe",
  "despegar.com.pe",
  "skyscanner.com.pe",
  "rome2rio.com",
  "tripadvisor.com.pe",
];

const outDir = new URL("../public/logos/", import.meta.url);
await mkdir(outDir, { recursive: true });

for (const domain of DOMAINS) {
  const logo = (await fetchLogo(domain)) ?? (await fetchLogo(`www.${domain}`));
  if (!logo) {
    console.log(`skip ${domain}: no logo`);
    continue;
  }
  await writeFile(new URL(`${domain}.png`, outDir), logo);
  console.log(`ok   ${domain} (${logo.length} B)`);
}

async function fetchLogo(host) {
  const response = await fetch(`https://www.google.com/s2/favicons?domain=${host}&sz=64`);
  // A missing favicon comes back as a generic globe with status 404.
  if (!response.ok) return null;
  return Buffer.from(await response.arrayBuffer());
}
