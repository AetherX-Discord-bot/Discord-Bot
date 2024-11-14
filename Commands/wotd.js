module.exports = {
    data: new SlashCommandBuilder()
      .setName('wotd')
      .setDescription('Provides the word of the day with definition and history'),
  
    async execute(interaction) {
      // Make an API request to Wordnik for the WOTD
      try {
        const response = await axios.get(`https://api.wordnik.com/v4/words.json/wordOfTheDay`, {
          params: { api_key: WORDNIK_API_KEY },
        });
  
        const wordData = response.data;
        const { word, definitions, examples, note } = wordData;
  
        // Create embed for word data
        const embed = {
          color: 0x3498db,
          title: `Word of the Day: ${word}`,
          fields: [
            { name: 'Definition', value: definitions[0]?.text || 'No definition found' },
            { name: 'Example', value: examples[0]?.text || 'No example available' },
            { name: 'Etymology', value: note || 'No etymology found' },
          ],
        };
  
        await interaction.reply({ embeds: [embed] });
      } catch (error) {
        console.error(error);
        await interaction.reply("Sorry, I couldn't fetch the Word of the Day.");
      }
    },
  };