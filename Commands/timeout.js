const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('timeout')
        .setDescription('Temporarily timeout a user in the server')
        .addUserOption(option => 
            option.setName('user')
                .setDescription('The user to timeout')
                .setRequired(true))
        .addIntegerOption(option => 
            option.setName('duration')
                .setDescription('Duration in minutes for the timeout')
                .setRequired(true))
        .addStringOption(option => 
            option.setName('reason')
                .setDescription('Reason for the timeout')
                .setRequired(false)),
    
    async execute(interaction) {
        await interaction.deferReply();

        // Check if the user has the required permissions
        if (!interaction.member.permissions.has(PermissionsBitField.Flags.ModerateMembers) &&
            !interaction.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return interaction.editReply("You don't have permission to use this command.");
        }

        const user = interaction.options.getUser('user');
        const duration = interaction.options.getInteger('duration');
        const reason = interaction.options.getString('reason') || 'No reason provided';
        const member = await interaction.guild.members.fetch(user.id);

        if (!member) {
            return interaction.editReply('User not found.');
        }

        try {
            await member.timeout(duration * 60 * 1000, reason);
            await interaction.editReply(`${user.tag} has been timed out for ${duration} minutes. Reason: ${reason}`);
        } catch (error) {
            console.error(error);
            await interaction.editReply('Failed to timeout the user.');
        }
    }
};