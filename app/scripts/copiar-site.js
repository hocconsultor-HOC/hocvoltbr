// Copia o site (pasta acima) para www/, para o app ter exatamente o mesmo layout e a mesma lógica.
// Também embute a base diária (data/brasil.json), quando existir, para o app abrir já com dados.
const fs = require("fs"), path = require("path");
const raiz = path.resolve(__dirname, "..", "..");
const www = path.resolve(__dirname, "..", "www");
fs.rmSync(www, { recursive: true, force: true });
fs.mkdirSync(www, { recursive: true });
const copiar = (rel) => {
  const de = path.join(raiz, rel), para = path.join(www, rel);
  if (!fs.existsSync(de)) return;
  fs.mkdirSync(path.dirname(para), { recursive: true });
  fs.cpSync(de, para, { recursive: true });
  console.log("copiado:", rel);
};
["index.html", "manifest.webmanifest", "privacidade.html", "icons", "data/brasil.json", "data/meta.json"].forEach(copiar);
if (!fs.existsSync(path.join(www, "index.html"))) { console.error("index.html do site não encontrado em " + raiz); process.exit(1); }

// Preenche, só dentro do app, o endereço do site publicado (para baixar a base das 23h59)
// e a chave do Open Charge Map (vinda do "secret" OCM_KEY do GitHub). O site original não é alterado.
const idx = path.join(www, "index.html");
let html = fs.readFileSync(idx, "utf8");
const base = (process.env.RV_BASE_REMOTA || "").trim();
const ocm = (process.env.RV_OCM_KEY || "").trim();
if (base) html = html.replace('const BASE_REMOTA = "";', "const BASE_REMOTA = " + JSON.stringify(base.endsWith("/") ? base : base + "/") + ";");
if (ocm) html = html.replace('const OCM_KEY_DEFAULT = "";', "const OCM_KEY_DEFAULT = " + JSON.stringify(ocm) + ";");
fs.writeFileSync(idx, html);
console.log("base remota:", base || "(não definida)", "| chave OCM:", ocm ? "embutida" : "(não definida)");
