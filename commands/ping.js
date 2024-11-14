const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('ping')
        .setDescription('Replies with the bot latency.'),

    async execute(interaction) {
        const sent = Date.now();
        await interaction.reply({ content: 'Pinging...', ephemeral: true }); // Makes the initial response ephemeral
        const timeTaken = Date.now() - sent;
        await interaction.editReply({ content: `Pong! Latency is ${timeTaken}ms. API Latency is ${Math.round(interaction.client.ws.ping)}ms.` });
    },
};