const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const localtunnel = require('localtunnel');
const config = require('./config.json');

const PORT = 8765;
const PY_API_URL = 'http://localhost:5000/guild_count';
const subdomain = config.WEBSERVER_SUBDOMAIN || 'ksjisudhshsh';

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
      }
    } catch (e) {
      ws.send(JSON.stringify({ type: 'error', message: e.toString() }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`Web server and WebSocket running on http://localhost:${PORT}`);
});
