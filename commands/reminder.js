const { SlashCommandBuilder } = require('@discordjs/builders');
const { MessageActionRow, MessageButton } = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('remind')
    .setDescription('Set a reminder')
    .addStringOption(option =>
      option.setName('message')
        .setDescription('What do you want to be reminded about?')
        .setRequired(true))
    .addStringOption(option =>
      option.setName('location')
        .setDescription('Where do you want to receive the reminder?')
        .setRequired(true)
        .addChoices(
          { name: 'Server', value: 'server' },
          { name: 'DM', value: 'dm' },
        ))
    .addStringOption(option =>
      option.setName('time')
        .setDescription('When do you want to be reminded? (format: YYYY-MM-DD HH:MM)')
        .setRequired(true)),

  async execute(interaction) {
    const message = interaction.options.getString('message');
    const location = interaction.options.getString('location');
    const timeString = interaction.options.getString('time');
    
    // Parse the time and validate it
    const reminderTime = new Date(timeString);

    if (isNaN(reminderTime.getTime())) {
      return interaction.reply({ content: 'Invalid time format. Please use YYYY-MM-DD HH:MM.', ephemeral: true });
    }

    const timeUntilReminder = reminderTime.getTime() - Date.now();
    if (timeUntilReminder <= 0) {
      return interaction.reply({ content: 'The time must be in the future.', ephemeral: true });
    }

    // Acknowledge the reminder set
    await interaction.reply({ content: `Reminder set for "${message}" at ${reminderTime.toLocaleString()}.`, ephemeral: true });

    // Schedule the reminder
    setTimeout(async () => {
      const reminderMessage = `Reminder: ${message}`;

      if (location === 'server') {
        await interaction.followUp({ content: reminderMessage });
      } else if (location === 'dm') {
        try {
          await interaction.user.send(reminderMessage);
        } catch (err) {
          console.error('Failed to send DM:', err);
        }
      }
    }, timeUntilReminder);
  },
};