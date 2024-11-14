clear
// Helper function to log errors to a file
function logErrorToFile(error) {
    const errorMessage = `[${new Date().toISOString()}] ${error}\n`;
    fs.appendFile('error.log', errorMessage, (err) => {
        if (err) console.error('Failed to write to log file:', err);
    });
}

// Define the command
module.exports = {
    data: new SlashCommandBuilder()
        .setName('gif')
        .setDescription('Search for a GIF')
        .addStringOption(option => 
            option.setName('query')
                .setDescription('The search term for the GIF')
                .setRequired(true)),
    async execute(interaction) {
        const query = interaction.options.getString('query');
        const GIPHY_API_KEY = process.env.GIPHY_API_KEY;

        try {
            const response = await axios.get(`https://api.giphy.com/v1/gifs/search`, {
                params: {
                    api_key: GIPHY_API_KEY,
                    q: query,
                    limit: 1,
                    rating: 'g'
                }
            });

            if (response.data.data.length === 0) {
                return interaction.reply('No GIFs found for that search term.');
            }

            const gifUrl = response.data.data[0].images.original.url;

            const embed = {
                color: 0x0099ff,
                title: `Here's a GIF for: ${query}`,
                image: { url: gifUrl },
                footer: { text: 'Powered by Giphy' }
            };

            await interaction.reply({ embeds: [embed] });
        } catch (error) {
            console.error('Error fetching GIF:', error);
            logErrorToFile(error);
            await interaction.reply('Sorry, I couldn\'t find a GIF right now!');
        }
    }
};