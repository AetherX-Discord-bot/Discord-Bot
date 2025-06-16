// This file contains helper functions for Discord OAuth2 validation and API calls
const axios = require('axios');
const config = require('../config.json');

const DISCORD_API = 'https://discord.com/api/v10';

async function validateOAuth2Token(token) {
  try {
    const resp = await axios.get(`${DISCORD_API}/oauth2/applications/@me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    // Check if the token is for the correct application
    if (resp.data.id && resp.data.id === config.APPLICATION_ID.toString()) {
      return true;
    }
    return false;
  } catch (err) {
    return false;
  }
}

async function getUserGuilds(token) {
  try {
    const resp = await axios.get(`${DISCORD_API}/users/@me/guilds`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return resp.data;
  } catch (err) {
    return null;
  }
}

async function getGuildSettings(guildId, token) {
  // Placeholder: Replace with your own logic to fetch and update settings
  // For now, just return a mock object
  return { guildId, settings: { prefix: '!', welcomeMessage: 'Welcome!' } };
}

async function updateGuildSettings(guildId, token, newSettings) {
  // Placeholder: Replace with your own logic to update settings
  // For now, just return the new settings
  return { guildId, settings: newSettings };
}

module.exports = {
  validateOAuth2Token,
  getUserGuilds,
  getGuildSettings,
  updateGuildSettings
};
