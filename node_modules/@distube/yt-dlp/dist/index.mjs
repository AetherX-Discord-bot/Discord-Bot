var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// ../../node_modules/.pnpm/tsup@8.1.0_postcss@8.4.38_ts-node@10.9.2_@types+node@20.14.2_typescript@5.4.5__typescript@5.4.5/node_modules/tsup/assets/esm_shims.js
import { fileURLToPath } from "url";
import path from "path";
var getFilename = /* @__PURE__ */ __name(() => fileURLToPath(import.meta.url), "getFilename");
var getDirname = /* @__PURE__ */ __name(() => path.dirname(getFilename()), "getDirname");
var __dirname = /* @__PURE__ */ getDirname();

// src/wrapper.ts
import dargs from "dargs";
import fs from "node:fs/promises";
import { spawn } from "node:child_process";
import { request } from "undici";

// src/env.ts
import path2 from "path";
var e = /* @__PURE__ */ __name((key) => process.env[key], "e");
var YTDLP_DISABLE_DOWNLOAD = !!e("YTDLP_DISABLE_DOWNLOAD");
var YTDLP_URL = e("YTDLP_URL");
var YTDLP_IS_WINDOWS = e("YTDLP_IS_WINDOWS") || process.platform === "win32";
var YTDLP_DIR = e("YTDLP_DIR") || path2.join(__dirname, "..", "bin");
var YTDLP_FILENAME = e("YTDLP_FILENAME") || `yt-dlp${YTDLP_IS_WINDOWS ? ".exe" : ""}`;
var YTDLP_PATH = path2.join(YTDLP_DIR, YTDLP_FILENAME);

// src/wrapper.ts
var makeRequest = /* @__PURE__ */ __name(async (url) => {
  const response = await request(url, { headers: { "user-agent": "distube" } });
  if (!response.statusCode) throw new Error(`Cannot make requests to '${url}'`);
  if (response.statusCode.toString().startsWith("3")) {
    if (!response.headers.location || Array.isArray(response.headers.location)) {
      throw new Error(`Cannot redirect to '${url}'`);
    }
    for await (const _chunk of response.body) {
    }
    return makeRequest(response.headers.location);
  }
  if (response.statusCode.toString().startsWith("2")) return response;
  throw new Error(`${url}
Status code ${response.statusCode.toString()}`);
}, "makeRequest");
var args = /* @__PURE__ */ __name((url, flags = {}) => [url].concat(dargs(flags, { useEquals: false })).filter(Boolean), "args");
var json = /* @__PURE__ */ __name((url, flags, options) => {
  const process2 = spawn(YTDLP_PATH, args(url, flags), options);
  return new Promise((resolve, reject) => {
    let output = "";
    process2.stdout?.on("data", (chunk) => {
      output += chunk;
    });
    process2.stderr?.on("data", (chunk) => {
      output += chunk;
    });
    process2.on("close", (code) => {
      if (code === 0) resolve(JSON.parse(output));
      else reject(new Error(output));
    });
    process2.on("error", reject);
  });
}, "json");
var binContentTypes = ["binary/octet-stream", "application/octet-stream", "application/x-binary"];
var getBinary = /* @__PURE__ */ __name(async (url) => {
  let version = "N/A";
  if (!url) {
    const defaultFilename = `yt-dlp${YTDLP_IS_WINDOWS ? ".exe" : ""}`;
    const defaultUrl = `https://github.com/yt-dlp/yt-dlp/releases/latest/download/${defaultFilename}`;
    try {
      const response2 = await makeRequest("https://api.github.com/repos/yt-dlp/yt-dlp/releases?per_page=1");
      const [{ assets, tag_name }] = await response2.body.json();
      const { browser_download_url } = assets.find(
        ({ name }) => name === `yt-dlp${YTDLP_IS_WINDOWS ? ".exe" : ""}`
      );
      version = typeof tag_name === "string" ? tag_name : "latest";
      url = typeof browser_download_url === "string" ? browser_download_url : defaultUrl;
    } catch {
      version = "latest";
      url = defaultUrl;
    }
  }
  const response = await makeRequest(url);
  const contentType = response.headers["content-type"]?.toString();
  if (binContentTypes.includes(contentType ?? "")) return { buffer: await response.body.arrayBuffer(), version };
  throw new Error(`Unsupported content type: ${contentType}`);
}, "getBinary");
var download = /* @__PURE__ */ __name(() => Promise.all([getBinary(YTDLP_URL), fs.mkdir(YTDLP_DIR, { recursive: true }).catch(() => void 0)]).then(
  ([{ buffer, version }]) => {
    fs.writeFile(YTDLP_PATH, Buffer.from(buffer), { mode: 493 });
    return version;
  }
), "download");

// src/index.ts
import { DisTubeError, PlayableExtractorPlugin, Playlist, Song } from "distube";
var isPlaylist = /* @__PURE__ */ __name((i) => Array.isArray(i.entries), "isPlaylist");
var YtDlpPlugin = class extends PlayableExtractorPlugin {
  static {
    __name(this, "YtDlpPlugin");
  }
  constructor({ update } = {}) {
    super();
    if (update ?? true) download().catch(() => void 0);
  }
  init(distube) {
    super.init(distube);
    if (this.distube.plugins[this.distube.plugins.length - 1] !== this) {
      console.warn(
        `[${this.constructor.name}] This plugin is not the last plugin in distube. This is not recommended.`
      );
    }
  }
  validate() {
    return true;
  }
  async resolve(url, options) {
    const info = await json(url, {
      dumpSingleJson: true,
      noWarnings: true,
      noCallHome: true,
      preferFreeFormats: true,
      skipDownload: true,
      simulate: true
    }).catch((e2) => {
      throw new DisTubeError("YTDLP_ERROR", `${e2.stderr || e2}`);
    });
    if (isPlaylist(info)) {
      if (info.entries.length === 0) throw new DisTubeError("YTDLP_ERROR", "The playlist is empty");
      return new Playlist(
        {
          source: info.extractor,
          songs: info.entries.map((i) => new YtDlpSong(this, i, options)),
          id: info.id.toString(),
          name: info.title,
          url: info.webpage_url,
          thumbnail: info.thumbnails?.[0]?.url
        },
        options
      );
    }
    return new YtDlpSong(this, info, options);
  }
  async getStreamURL(song) {
    if (!song.url) {
      throw new DisTubeError("YTDLP_PLUGIN_INVALID_SONG", "Cannot get stream url from invalid song.");
    }
    const info = await json(song.url, {
      dumpSingleJson: true,
      noWarnings: true,
      noCallHome: true,
      preferFreeFormats: true,
      skipDownload: true,
      simulate: true,
      format: "ba/ba*"
    }).catch((e2) => {
      throw new DisTubeError("YTDLP_ERROR", `${e2.stderr || e2}`);
    });
    if (isPlaylist(info)) throw new DisTubeError("YTDLP_ERROR", "Cannot get stream URL of a entire playlist");
    return info.url;
  }
  getRelatedSongs() {
    return [];
  }
};
var YtDlpSong = class extends Song {
  static {
    __name(this, "YtDlpSong");
  }
  constructor(plugin, info, options = {}) {
    super(
      {
        plugin,
        source: info.extractor,
        playFromSource: true,
        id: info.id,
        name: info.title || info.fulltitle,
        url: info.webpage_url || info.original_url,
        isLive: info.is_live,
        thumbnail: info.thumbnail || info.thumbnails?.[0]?.url,
        duration: info.is_live ? 0 : info.duration,
        uploader: {
          name: info.uploader,
          url: info.uploader_url
        },
        views: info.view_count,
        likes: info.like_count,
        dislikes: info.dislike_count,
        reposts: info.repost_count,
        ageRestricted: Boolean(info.age_limit) && info.age_limit >= 18
      },
      options
    );
  }
};
export {
  YtDlpPlugin,
  download,
  json
};
//# sourceMappingURL=index.mjs.map