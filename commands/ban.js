const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder, PermissionsBitField } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('ban')
        .setDescription('Ban a user from the server')
        .addUserOption(option => 
            option.setName('user')
                .setDescription('The user to ban')
                .setRequired(true))
        .addStringOption(option => 
            option.setName('reason')
                .setDescription('Reason for the ban')
                .setRequired(false)),
    
    async execute(interaction) {
        await interaction.deferReply(); // Prevents the 3-second timeout issue

        // Check if the user has the required permissions
        if (!interaction.member.permissions.has(PermissionsBitField.Flags.BanMembers) &&
            !interaction.member.permissions.has(PermissionsBitField.Flags.Administrator)) {
            return interaction.editReply("You don't have permission to use this command.");
        }

        const user = interaction.options.getUser('user');
        const reason = interaction.options.getString('reason') || 'No reason provided';
        const member = await interaction.guild.members.fetch(user.id);

        if (!member) {
            return interaction.editReply('User not found.');
        }

        try {
            await member.ban({ reason });
            await interaction.editReply(`${user.tag} has been banned. Reason: ${reason}`);
        } catch (error) {
            console.error(error);
            await interaction.editReply('Failed to ban the user.');
        }
    }
};