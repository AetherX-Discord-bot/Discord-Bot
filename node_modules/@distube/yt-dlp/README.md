<div align="center">
  <p>
    <a href="https://nodei.co/npm/@distube/yt-dlp"><img src="https://nodei.co/npm/@distube/yt-dlp.png?downloads=true&downloadRank=true&stars=true"></a>
  </p>
  <p>
    <img alt="npm peer dependency version" src="https://img.shields.io/npm/dependency-version/@distube/yt-dlp/peer/distube?style=flat-square">
    <img alt="npm" src="https://img.shields.io/npm/dt/@distube/yt-dlp?logo=npm&style=flat-square">
    <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/distubejs/extractor-plugins?logo=github&logoColor=white&style=flat-square">
    <a href="https://discord.gg/feaDd9h"><img alt="Discord" src="https://img.shields.io/discord/732254550689316914?logo=discord&logoColor=white&style=flat-square"></a>
  </p>
  <p>
    <a href='https://ko-fi.com/skick' target='_blank'><img height='48' src='https://storage.ko-fi.com/cdn/kofi3.png' alt='Buy Me a Coffee at ko-fi.com' /></a>
  </p>
</div>

# @distube/yt-dlp

A DisTube playable extractor plugin using [yt-dlp](https://github.com/yt-dlp/yt-dlp)

[_What is a playable extractor plugin?_](https://github.com/skick1234/DisTube/wiki/Projects-Hub#plugins)

# Feature

- Support [900+ sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) using [yt-dlp](https://github.com/yt-dlp/yt-dlp)

# Requirement

- [python](https://www.python.org/)

# Installation

```sh
npm install @distube/yt-dlp@latest
```

# Usage

```ts
import { DisTube } from "distube";
import { YtDlpPlugin } from "@distube/yt-dlp";

const distube = new DisTube(client, {
  plugins: [new YtDlpPlugin({ update: true })],
});
```

# Documentation

### new YtDlpPlugin([YtDlpPluginOptions])

Create a DisTube's `ExtractorPlugin` instance.

- `YtDlpPluginOptions.update` (`boolean`): Default is `true`. Update the yt-dlp binary when the plugin is initialized.

> YtDlpPlugin should be the last plugin in the `plugins` array.

## Environment Variables

- `YTDLP_DISABLE_DOWNLOAD`: Set it to disable download yt-dlp binary.
- `YTDLP_URL`: The URL of the yt-dlp binary to download.
- `YTDLP_DIR`: The directory to download the yt-dlp binary.
- `YTDLP_FILENAME`: The filename of the yt-dlp binary.

## Troubleshooting

### Failed to install (Status code: 403)

Your IP has been rate-limited by GitHub and the plugin cannot get the latest link to the yt-dlp binary.
You can change the download link by using the environment variable `YTDLP_URL`, or disable download by setting `YTDLP_DISABLE_DOWNLOAD` to `true`.

```sh
export YTDLP_URL=https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
npm install @distube/yt-dlp@latest
```

```sh
export YTDLP_DISABLE_DOWNLOAD=true
npm install @distube/yt-dlp@latest
```

### Failed to run the plugin (Status code: 403)

The plugin cannot download the yt-dlp binary on startup. Same as the previous case.
You can disable download on startup by using `new YtDlpPlugin({ update: false })` or using above solution.

```js
import { DisTube } from "distube";
const distube = new DisTube(client, {
  plugins: [new YtDlpPlugin({ update: false })],
});
```
