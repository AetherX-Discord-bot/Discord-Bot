const { SlashCommandBuilder } = require('@discordjs/builders');
const { EmbedBuilder } = require('discord.js');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('about')
        .setDescription('Shows information about the bot'),
    
    async execute(interaction) {
        const aboutEmbed = new EmbedBuilder()
            .setColor(0x7289da) // Discord's blurple color
            .setTitle('AetherX Bot Information')
            .setDescription('AetherX is a custom Discord bot designed by Androgalaxi and lmutt090.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8) or the link below.')
            .addFields(
                { name: 'Developer', value: '[Androgalaxi](https://discord.com/users/435125886996709377) and [lmutt090](https://discord.com/users/1286383453016686705)' },
                { name: 'Bot Version', value: '1.0.0' },
                { name: 'Bot Invite Link', value: '[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8)' },
                { name: 'Support Server', value: '[Join the Support Server](https://discord.gg/yFY8Fnbtp9)' }
            )
            .setFooter({ text: 'AetherX Bot - Created with suffering by Androgalaxi and lmutt090' });

        await interaction.reply({ embeds: [aboutEmbed] });
    },
};