const { SlashCommandBuilder } = require('@discordjs/builders'); // Import command builder

module.exports = {
  data: new SlashCommandBuilder()
    .setName('setstatus')
    .setDescription('Change the bot’s status')
    .addStringOption(option =>
      option.setName('type')
        .setDescription('The type of status (online, idle, dnd, invisible)')
        .setRequired(true)
        .addChoices(
          { name: 'Online', value: 'online' },
          { name: 'Idle', value: 'idle' },
          { name: 'Do Not Disturb', value: 'dnd' },
          { name: 'Invisible', value: 'invisible' }
        ))
    .addStringOption(option =>
      option.setName('message')
        .setDescription('The custom status message')
        .setRequired(true)),
  
  async execute(interaction) {
    const allowedUsers = ['435125886996709377', '1286383453016686705']; // IDs allowed to use this command
    const userId = interaction.user.id;

    // Check if the user has permission
    if (!allowedUsers.includes(userId)) {
      return interaction.reply({
        content: "You do not have permission to use this command.",
        ephemeral: true
      });
    }

    const type = interaction.options.getString('type'); // Gets the status type (online, idle, etc.)
    const message = interaction.options.getString('message'); // Gets the custom message

    // Set the bot's presence
    interaction.client.user.setPresence({
      status: type,
      activities: [{ name: message }]
    });

    await interaction.reply(`Status updated to **${type}** with message: "${message}"`);
  }
};