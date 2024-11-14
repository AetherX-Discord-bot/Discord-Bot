const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('unmute')
        .setDescription('Unmute a user in the server')
        .addUserOption(option => 
            option.setName('user')
                .setDescription('The user to unmute')
                .setRequired(true)),
    
    async execute(interaction) {
        await interaction.deferReply();

        // Check if the user has the required permissions
        if (!interaction.member.permissions.has(PermissionsBitField.Flags.ModerateMembers) &&
            !interaction.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return interaction.editReply("You don't have permission to use this command.");
        }

        const user = interaction.options.getUser('user');
        const member = await interaction.guild.members.fetch(user.id);

        if (!member) {
            return interaction.editReply('User not found.');
        }

        try {
            await member.timeout(null); // Removes the timeout
            await interaction.editReply(`${user.tag} has been unmuted.`);
        } catch (error) {
            console.error(error);
            await interaction.editReply('Failed to unmute the user.');
        }
    }
};
