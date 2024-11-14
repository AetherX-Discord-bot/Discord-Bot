const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('say')
        .setDescription('Send a message as the bot in the current channel.')
        .addStringOption(option => 
            option.setName('message')
                .setDescription('The message to send')
                .setRequired(true)
        ),
    async execute(interaction) {
        // Get the message from the command options
        const message = interaction.options.getString('message');
        
        // Defer reply to prevent the user from seeing the command confirmation
        await interaction.deferReply({ ephemeral: true });
        
        // Send the message in the channel the command was used in
        await interaction.channel.send(message);

        // Reply to the user in an ephemeral message so only they can see it
        await interaction.editReply({ content: 'Message sent!', ephemeral: true });
    }
};