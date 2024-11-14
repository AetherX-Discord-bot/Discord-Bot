const { SlashCommandBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('restart')
        .setDescription('Restarts the bot (restricted to certain users)'),
    async execute(interaction) {
        const allowedUsers = ['435125886996709377', '1286383453016686705', '1123769629165244497'];

        if (!allowedUsers.includes(interaction.user.id)) {
            return interaction.reply({ content: "You don't have permission to use this command.", ephemeral: true });
        }

        await interaction.reply('Restarting bot...');
        
        setTimeout(() => {
            process.exit(0); // Restarts the bot if managed by start.bat
        }, 1000); // Allows reply to send before exiting
    },
};
