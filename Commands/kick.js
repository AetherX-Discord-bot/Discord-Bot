const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('kick')
        .setDescription('Kick a user from the server')
        .addUserOption(option => 
            option.setName('user')
                .setDescription('The user to kick')
                .setRequired(true))
        .addStringOption(option => 
            option.setName('reason')
                .setDescription('Reason for the kick')
                .setRequired(false)),
    
    async execute(interaction) {
        await interaction.deferReply();

        const user = interaction.options.getUser('user');
        const reason = interaction.options.getString('reason') || 'No reason provided';
        const member = await interaction.guild.members.fetch(user.id);

        if (!member) {
            return interaction.editReply('User not found.');
        }

        // Check if the user executing the command is the same as the user being kicked
        const isSelfKick = interaction.user.id === user.id;

        // Only perform permission check if it's not a self-kick
        if (!isSelfKick && 
            !interaction.member.permissions.has(PermissionsBitField.Flags.KickMembers) &&
            !interaction.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return interaction.editReply("You don't have permission to use this command.");
        }

        try {
            await member.kick(reason);
            await interaction.editReply(`${user.tag} has been kicked. Reason: ${reason}`);
        } catch (error) {
            console.error(error);
            await interaction.editReply('Failed to kick the user.');
        }
    }
};
