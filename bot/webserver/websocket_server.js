const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const localtunnel = require('localtunnel');
const config = require('../config.json');
const oauthHelpers = require('./oauth_helpers.js');

const PORT = 8765;
const PY_API_URL = 'http://localhost:5000/guild_count';
const subdomain = config.WEBSERVER_SUBDOMAIN || 'ksjisudhsh';

// Create a localtunnel to expose the WebSocket server
localtunnel(PORT, { subdomain }).then((tunnel) => {
  console.log(`Localtunnel running at ${tunnel.url}`);
}).catch((err) => {
  console.error('Error starting localtunnel:', err);
});

// Simple HTTP server to serve an index.html file
const server = http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html') {
    const filePath = path.join(__dirname, 'index.html');
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Error loading index.html');
      } else {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(data);
      }
    });
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

const wss = new WebSocket.Server({ server });

wss.on('connection', function connection(ws) {
  ws.on('message', async function incoming(message) {
    try {
      const data = JSON.parse(message);
      if (data.type === 'get-bot-guild-count') {
        // Fetch from Python Flask API
        try {
          const response = await axios.get(PY_API_URL);
          ws.send(JSON.stringify({ type: 'bot-guild-count', count: response.data.guild_count }));
        } catch (err) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to fetch guild count from Python API' }));
        }
      } else if (data.type === 'get-guild-settings') {
        // Requires: { type: 'get-guild-settings', token, guildId }
        if (!data.token || !data.guildId) {
          ws.send(JSON.stringify({ type: 'error', message: 'Missing token or guildId' }));
          return;
        }
        const valid = await oauthHelpers.validateOAuth2Token(data.token);
        if (!valid) {
          ws.send(JSON.stringify({ type: 'error', message: 'Invalid or unauthorized OAuth2 token' }));
          return;
        }
        // Fetch settings and guild info from Python API
        try {
          const settingsResp = await oauthHelpers.getGuildSettings(data.guildId, data.token);
          const infoResp = await axios.get(`http://localhost:5000/guild_info?guild_id=${data.guildId}`);
          ws.send(JSON.stringify({
            type: 'guild-settings',
            guildId: data.guildId,
            settings: settingsResp,
            guildInfo: infoResp.data
          }));
        } catch (err) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to fetch guild info/settings.' }));
        }
      } else if (data.type === 'update-guild-settings') {
        // Requires: { type: 'update-guild-settings', token, guildId, newSettings }
        if (!data.token || !data.guildId || !data.newSettings) {
          ws.send(JSON.stringify({ type: 'error', message: 'Missing token, guildId, or newSettings' }));
          return;
        }
        const valid = await oauthHelpers.validateOAuth2Token(data.token);
        if (!valid) {
          ws.send(JSON.stringify({ type: 'error', message: 'Invalid or unauthorized OAuth2 token' }));
          return;
        }
        const updated = await oauthHelpers.updateGuildSettings(data.guildId, data.token, data.newSettings);
        ws.send(JSON.stringify({ type: 'guild-settings-updated', guildId: data.guildId, settings: updated }));
      } else if (data.type === 'get-guild-members') {
        // Requires: { type: 'get-guild-members', token, guildId }
        if (!data.token || !data.guildId) {
          ws.send(JSON.stringify({ type: 'error', message: 'Missing token or guildId' }));
          return;
        }
        const valid = await oauthHelpers.validateOAuth2Token(data.token);
        if (!valid) {
          ws.send(JSON.stringify({ type: 'error', message: 'Invalid or unauthorized OAuth2 token' }));
          return;
        }
        // This should call the Python API to get members, or you can implement a REST endpoint for this
        try {
          const response = await axios.get(`http://localhost:5000/guild_members?guild_id=${data.guildId}`);
          ws.send(JSON.stringify({ type: 'guild-members', guildId: data.guildId, members: response.data.members }));
        } catch (err) {
          ws.send(JSON.stringify({ type: 'guild-members', guildId: data.guildId, members: null }));
        }
      } else if (data.type === 'kick-member') {
        // Requires: { type: 'kick-member', token, guildId, userId }
        if (!data.token || !data.guildId || !data.userId) {
          ws.send(JSON.stringify({ type: 'error', message: 'Missing token, guildId, or userId' }));
          return;
        }
        const valid = await oauthHelpers.validateOAuth2Token(data.token);
        if (!valid) {
          ws.send(JSON.stringify({ type: 'error', message: 'Invalid or unauthorized OAuth2 token' }));
          return;
        }
        try {
          await axios.post('http://localhost:5000/kick_member', { guild_id: data.guildId, user_id: data.userId, token: data.token });
          ws.send(JSON.stringify({ type: 'success', message: 'Member kicked.' }));
        } catch (err) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to kick member.' }));
        }
      } else if (data.type === 'ban-member') {
        // Requires: { type: 'ban-member', token, guildId, userId }
        if (!data.token || !data.guildId || !data.userId) {
          ws.send(JSON.stringify({ type: 'error', message: 'Missing token, guildId, or userId' }));
          return;
        }
        const valid = await oauthHelpers.validateOAuth2Token(data.token);
        if (!valid) {
          ws.send(JSON.stringify({ type: 'error', message: 'Invalid or unauthorized OAuth2 token' }));
          return;
        }
        try {
          await axios.post('http://localhost:5000/ban_member', { guild_id: data.guildId, user_id: data.userId, token: data.token });
          ws.send(JSON.stringify({ type: 'success', message: 'Member banned.' }));
        } catch (err) {
          ws.send(JSON.stringify({ type: 'error', message: 'Failed to ban member.' }));
        }
      }
    } catch (e) {
      ws.send(JSON.stringify({ type: 'error', message: e.toString() }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`Web server and WebSocket running on http://localhost:${PORT}`);
});
