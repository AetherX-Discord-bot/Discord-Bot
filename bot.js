// Import the necessary modules
require('dotenv').config();
const { Client, GatewayIntentBits, ButtonBuilder, ButtonStyle, ActionRowBuilder, EmbedBuilder, ComponentType } = require('discord.js');
const { DisTube } = require('distube');
const { YtDlpPlugin } = require('@distube/yt-dlp');
const { SpotifyPlugin } = require('@distube/spotify');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v10');
const afkUsers = new Map();
const axios = require('axios');
const he = require('he');

// Create a new Discord client with intents to listen for messages
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.DirectMessages,
        GatewayIntentBits.GuildPresences // Add this line for presence intent
    ]
});

// Logging for any errors that are not caught in the terminal
process.on('unhandledRejection', (error) => {
    console.error('Unhandled promise rejection:', error);
});

client.on('error', (error) => {
    console.error('Client error:', error);
});

// Slash command registration
const commands = [
    {
        name: 'about',
        description: 'Provides information about the bot, developer, and invites.'
    }
];

const rest = new REST({ version: '10' }).setToken('YOUR_BOT_TOKEN');

// Register the slash commands when the bot is ready
client.once('ready', async () => {
    try {
        console.log('Bot is online!');

        // Register commands globally
        await rest.put(
            Routes.applicationCommands(client.user.id),
            { body: commands } // Ensure "commands" is defined correctly elsewhere
        );

        // Set the bot's activity (this is basic activity, not full Rich Presence)
        await client.user.setActivity('with broken commands', { type: 'PLAYING' });
        console.log('Slash commands registered and bot activity set successfully.');
        
    } catch (error) {
        console.error('Error during bot setup:', error);
    }
});

const distube = new DisTube(client, {
    plugins: [new YtDlpPlugin(), new SpotifyPlugin({
        api: {
            clientId: process.env.SPOTIFY_CLIENT_ID,
            clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
        }
    })],
    emitNewSongOnly: true,  // Keep this if you only want to emit 'playSong' once
});


// Handle interactionCreate event for slash commands
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isCommand()) return;

    const { commandName } = interaction;

    if (commandName === 'about') {
        const aboutEmbed = new EmbedBuilder()
            .setColor(0x7289da) // Discord's blurple color
            .setTitle('AetherX Bot Information')
            .setDescription('AetherX is a custom Discord bot designed by Androgalaxi and lmutt090.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8) or the link below.')
            .addFields(
                { name: 'Developer', value: 'Androgalaxi and lmutt090' },
                { name: 'Bot Version', value: '1.0.0' },
                { name: 'Bot Invite Link', value: '[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8)' },
                { name: 'Support Server', value: '[Join the Support Server](https://discord.gg/yFY8Fnbtp9)' }
            )
            .setFooter({ text: 'AetherX Bot - Created with suffering by Androgalaxi and lmutt090' });

        await interaction.reply({ embeds: [aboutEmbed] });
    }
});

// Map to store the last help message for each user
const userHelpMessages = new Map();

// Function to send or edit help message based on the requested page
async function sendHelpMessage(message, page = 1) { // Default page is 1
    const helpPages = [
        {
            title: 'General Commands',
            description: '!changelog - Display changes made to the bot.\n!request - Request a feature or features to be added\n!afk - Go afk and set a custom message\n!ping - Displays the bot latency and API latency.\n!help - Shows this help menu with all available commands.\n!yippie - Sends a "Yippee" GIF.\n!global [message] - Sends a message to all servers where the bot is present.\n!about or !info - Provides information about the bot, developer, and invites.'
        },
        {
            title: 'Music Commands',
            description: '!play [song/URL] - Plays music from YouTube or Spotify, or searches for the song.\n!skip - Skips the currently playing song.\n!stop - Stops the music and clears the queue.\n!pause - Pauses the currently playing song.\n!resume - Resumes a paused song.\n!queue - Displays the current song queue.\n!skipto [number] - Skips to the song at the specified position in the queue.\n!volume [1-100] - Sets the volume of the music player.\n!nowplaying - Displays the currently playing song.\n!disconnect - Makes the bot leave the voice channel.\n!shuffle - Shuffles the current song queue.\n!lyrics [song name] - Fetches and displays the lyrics for the specified song.\n!seek [time] - Jumps to a specific time in the currently playing song.\n!repeat - Toggles repeat for the current song or the entire queue.\n!playlist [playlist name/URL] - Plays a specified playlist from a supported service.'
        },
        {
            title: 'Moderation Commands',
            description: '!ban [user] - Bans the mentioned user.\n!kick [user] - Kicks the mentioned user.\n!mute [user] - Mutes the mentioned user.\n!unmute [user] - Unmutes the mentioned user.\n!purge [amount] - Deletes a specified number of messages.\n!timeout [user] [time] - Times out a user for a specified duration.'
        },
        {
            title: 'Game Commands',
            description: '!blackjack or !bj - Play a game of BlackJack.\n!dnd - Roll the dice!\n!highlow or !hl - Play a game of HighLow\n!tictactoe or !ttt - Play a game of TicTacToe against another user or the bot\n !coinflip or !cf - Flip a coin\n!trivia or !quiz - Try to pick the correct answer on a random question\n !rockpaperscissors or !rps - Play a game of Rock Paper Scissors'
        }
    ];

    if (page < 1 || page > helpPages.length) {
        message.channel.send('Please provide a valid page number.');
        return;
    }

    const helpEmbed = new EmbedBuilder()
        .setColor(0x0099ff)
        .setTitle(helpPages[page - 1].title)
        .setDescription(helpPages[page - 1].description)
        .setFooter({ text: `Page ${page} of ${helpPages.length}` });

    // Create navigation buttons
    const row = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder()
                .setCustomId('previous')
                .setLabel('◀️ Previous')
                .setStyle(ButtonStyle.Primary)
                .setDisabled(page === 1), // Disable if on first page
            new ButtonBuilder()
                .setCustomId('next')
                .setLabel('Next ▶️')
                .setStyle(ButtonStyle.Primary)
                .setDisabled(page === helpPages.length) // Disable if on last page
        );

    // Check if the user has an existing help message
    const existingMessage = userHelpMessages.get(message.author.id);

    if (existingMessage) {
        await existingMessage.edit({ embeds: [helpEmbed], components: [row] });
    } else {
        const sentMessage = await message.channel.send({ embeds: [helpEmbed], components: [row] });
        userHelpMessages.set(message.author.id, sentMessage);

        // Create a collector to handle button interactions
        const filter = interaction => interaction.isButton() && 
                                      (interaction.customId === 'previous' || interaction.customId === 'next') &&
                                      interaction.user.id === message.author.id;

        const collector = sentMessage.createMessageComponentCollector({ filter, time: 60000 });

        collector.on('collect', async interaction => {
            // Update the page based on the button clicked
            if (interaction.customId === 'previous') {
                page -= 1;
            } else if (interaction.customId === 'next') {
                page += 1;
            }

            // Send the updated help message
            await sendHelpMessage(message, page);

            // Acknowledge the interaction
            await interaction.deferUpdate();
        });

        collector.on('end', () => {
            const helpMsg = userHelpMessages.get(message.author.id);
            if (helpMsg) {
                helpMsg.edit({ components: [] }); // Remove buttons after timeout
                userHelpMessages.delete(message.author.id); // Clear the message reference
            }
        });
    }
}

// Listen for the message "!help" to start the help command
client.on('messageCreate', async message => {
    if (message.content === '!help') {
        // Clear the previous help message for the user, if exists
        const existingMessage = userHelpMessages.get(message.author.id);
        if (existingMessage) {
            existingMessage.delete().catch(console.error);  // Delete the old help message
            userHelpMessages.delete(message.author.id);      // Clear the reference
        }

        // Send the new help message starting from page 1
        await sendHelpMessage(message);
    }
});

// Respond to specific messages
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    // Respond to !ping command and send latency
    if (message.content === '!ping') {
        const sent = Date.now();
        message.channel.send('Pinging...').then(sentMessage => {
            const timeTaken = Date.now() - sent;
            sentMessage.edit(`Pong! Latency is ${timeTaken}ms. API Latency is ${Math.round(client.ws.ping)}ms.`);
        });
    }


    // Respond to !say command
    client.on('messageCreate', async (message) => {
        // Ignore messages from bots
        if (message.author.bot) return;
    
        // Respond to !say command
        if (message.content.startsWith('!say')) {
            const sayMessage = message.content.slice('!say'.length).trim();
    
            if (!sayMessage) {
                return message.channel.send('Please provide a message for the bot to say.');
            }
    
            await message.channel.send({ content: sayMessage });
            await message.delete();
        }
    });    

    // Respond to !uptime command
    if (message.content === '!uptime') {
        const totalSeconds = (client.uptime / 1000);
        const days = Math.floor(totalSeconds / 86400);
        const hours = Math.floor((totalSeconds % 86400) / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);

        const uptime = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        message.channel.send(`I have been online for: ${uptime}`);
    }

    // Respond to !news command
    if (message.content === '!changelog') {
        const newsEmbed = new EmbedBuilder()
            .setColor(0x00ff00)
            .setTitle('Latest News')
            .setDescription(
                '**__Here are the latest updates:__**\n' +
                '* Fixed issues related to Music Commands\n\n'+
            
                '# Dev Notes\n'+
                'Currently we\'ve patched the issue related to Music Commands. We\'re currently not sure if this works or not as we\'re unable to test it.\n'+
                'If you notice a bug or want to suggest something while the bot is online use !request (type your message here).\n\n'+

                'We\'ll be working on patching the message issues related to Tic-Tac-Toe as well as Trivia/Quiz.'
            )
            .setFooter({ text: 'Changelog provided by AetherX Bot Devs' });

        message.channel.send({ embeds: [newsEmbed] });
    }

   
    // Respond to !yippie command and send the GIF or say "No yippe for you"
    if (message.content === '!yippie') {
        if (Math.random() < 0.01) {
            message.channel.send('No yippe for you');
        } else {
            message.channel.send('https://tenor.com/view/lethal-company-horderbug-yippee-gif-gif-5658063361159083327');
        }
    }
    
    if (message.content === 'shit') {
            message.channel.send('https://tse1.mm.bing.net/th/id/OIP.EDAz3VIJM7DB0aKqMAenOQHaNK?w=187&h=333&c=7&r=0&o=5&pid=1.7');
    }
    

    // Respond to !about or !info command with bot information
    if (message.content === '!about' || message.content === '!info') {
        const aboutEmbed = new EmbedBuilder()
            .setColor(0x7289da)
            .setTitle('AetherX Bot Information')
            .setDescription('AetherX is a custom Discord bot designed by Androgalaxi and lmutt090.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8) or the link below.')
            .addFields(
                { name: 'Developer', value: 'Androgalaxi and lmutt090' },
                { name: 'Bot Version', value: '1.0.0' },
                { name: 'Bot Invite Link', value: '[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8)' },
                { name: 'Support Server', value: '[Join the Support Server](https://discord.gg/yFY8Fnbtp9)' }
            )
            .setFooter({ text: 'AetherX Bot - Created with suffering by Androgalaxi and lmutt090' });

        message.channel.send({ embeds: [aboutEmbed] });
    }
});

    // Music commands
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    // Music commands
    if (message.content.startsWith('!play')) {
        // Extract the song name or URL
        const args = message.content.split(' ').slice(1).join(' ');

        // Check if the user is in a voice channel
        if (!message.member.voice.channel) {
            return message.channel.send('You need to be in a voice channel to play music!');
        }

        // Check if the user provided a song name or URL
        if (!args) {
            return message.channel.send('Please provide a song name or URL.');
        }

        try {
            // Play the song in the user's voice channel
            await distube.play(message.member.voice.channel, args, {
                member: message.member,
                textChannel: message.channel,
                message
            });

            message.channel.send(`🎶 Playing: ${args}`);
        } catch (error) {
            console.error(error);
            message.channel.send('There was an error trying to play that song. Please try again.');
        }
    }

    if (message.content === '!skip') {
        const queue = distube.getQueue(message);

        if (!queue) {
            return message.channel.send('There is nothing playing to skip.');
        }

        queue.skip();
        message.channel.send('Skipped the current song.');
    }

    if (message.content === '!stop') {
        const queue = distube.getQueue(message);

        if (!queue) {
            return message.channel.send('There is nothing playing to stop.');
        }

        queue.stop();
        message.channel.send('Stopped the music and cleared the queue.');
    }

    if (message.content === '!pause') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing playing to pause.');
        queue.pause();
        message.channel.send('Paused the current song.');
    }

    if (message.content === '!resume') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing to resume.');
        queue.resume();
        message.channel.send('Resumed the music.');
    }

    if (message.content === '!queue') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('The queue is empty.');
        message.channel.send(`Current queue:\n${queue.songs.map((song, id) =>
            `${id + 1}. ${song.name} - ${song.formattedDuration}`).join("\n")}`);
    }

    if (message.content.startsWith('!skipto')) {
        const args = parseInt(message.content.split(' ')[1]);
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is no queue to skip.');
        if (!args || isNaN(args) || args < 1 || args > queue.songs.length) {
            return message.channel.send('Invalid song number.');
        }
        queue.jump(args - 1);
        message.channel.send(`Skipped to song number ${args}.`);
    }

    if (message.content.startsWith('!volume')) {
        const args = parseInt(message.content.split(' ')[1]);
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing playing.');
        if (!args || isNaN(args) || args < 1 || args > 100) {
            return message.channel.send('Volume must be between 1 and 100.');
        }
        queue.setVolume(args);
        message.channel.send(`Set volume to ${args}%.`);
    }

    if (message.content === '!nowplaying') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing playing.');
        message.channel.send(`Now playing: ${queue.songs[0].name}`);
    }

    if (message.content === '!disconnect') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('I am not connected to a voice channel.');
        queue.voice.leave();
        message.channel.send('Disconnected from the voice channel.');
    }

    if (message.content === '!shuffle') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is no queue to shuffle.');
        queue.shuffle();
        message.channel.send('Shuffled the queue.');
    }

    if (message.content.startsWith('!lyrics')) {
        const args = message.content.split(' ').slice(1).join(' ');
        if (!args) return message.channel.send('Please provide the song name to get lyrics.');
        // Add your own lyrics fetching logic here, e.g., using an API
    }

    if (message.content.startsWith('!seek')) {
        const args = message.content.split(' ')[1];
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing playing.');
        const time = distube.parseTime(args);
        if (isNaN(time)) return message.channel.send('Invalid time.');
        queue.seek(time);
        message.channel.send(`Seeked to ${args}.`);
    }

    if (message.content === '!repeat') {
        const queue = distube.getQueue(message);
        if (!queue) return message.channel.send('There is nothing playing.');
        queue.toggleRepeatMode();
        message.channel.send(queue.repeatMode ? 'Repeat mode enabled.' : 'Repeat mode disabled.');
    }

    if (message.content.startsWith('!playlist')) {
        const args = message.content.split(' ').slice(1).join(' ');

        if (!message.member.voice.channel) {
            return message.channel.send('You need to be in a voice channel to play a playlist!');
        }

        if (!args) {
            return message.channel.send('Please provide a playlist name or URL.');
        }

        distube.playCustomPlaylist(message.member.voice.channel, args, {
            member: message.member,
            textChannel: message.channel,
            message
        });
    }
});

// Sends a DM to the Bot creator, Disabled if the Bot creator is in DND or "Offline"
// Ensure the function handling the request is asynchronous
client.on('messageCreate', async (message) => {
    if (message.content.startsWith('!request')) {
        const args = message.content.slice('!request'.length).trim(); // Get the message after the command

        // Check if there is any text provided after the command
        if (!args) {
            const errorEmbed = new EmbedBuilder()
                .setColor(0xff0000) // Red color for error
                .setTitle('Error')
                .setDescription('Please provide a feature or command request after `!request`.');
            return message.channel.send({ embeds: [errorEmbed] });
        }

        try {
            // List of user IDs to DM (Add more user IDs if needed)
            const userIds = ['435125886996709377', '1286383453016686705']; // Replace with your user IDs

            // Create an embed for the request
            const requestEmbed = new EmbedBuilder()
                .setColor(0x00ff00) // Green color for the request
                .setTitle('Feature/Command Request')
                .setDescription(`**From:** ${message.author.tag}\n\n**Request:** ${args}`)
                .setTimestamp();

            let unavailableCount = 0;
            let availableCount = 0;

            // Send the request to all users in the list
            for (const userId of userIds) {
                try {
                    const user = await message.client.users.fetch(userId); // Fetch user
                    const guildMember = message.guild.members.cache.get(userId);
                    const userPresence = guildMember?.presence?.status;

                    // Check if user is offline or in DND
                    if (userPresence === 'offline' || userPresence === 'dnd') {
                        unavailableCount++;
                        continue; // Skip DM if the user is unavailable
                    }

                    await user.send({ embeds: [requestEmbed] });
                    availableCount++; // Count the successfully sent DM
                } catch (error) {
                    console.error(`Failed to send DM to ${userId}:`, error);
                    unavailableCount++; // Increment unavailable count if there's an error
                }
            }

            // Create an embed to inform the user who made the request
            const feedbackEmbed = new EmbedBuilder().setTitle('Request Status').setTimestamp();

            if (unavailableCount === userIds.length) {
                feedbackEmbed
                    .setColor(0xff0000) // Red color for failure
                    .setDescription('All recipients are currently unavailable (DND or offline). Please try again later or send an email to fortnitefunny82.');
            } else if (unavailableCount > 0) {
                feedbackEmbed
                    .setColor(0xffa500) // Orange for partial success
                    .setDescription(`${unavailableCount} recipient(s) were unavailable, but your request was sent to ${availableCount} recipient(s).`);
            } else {
                feedbackEmbed
                    .setColor(0x00ff00) // Green for success
                    .setDescription('Your request has been sent to all recipients!');
            }

            // Send the feedback embed to the user in the same channel
            message.channel.send({ embeds: [feedbackEmbed] });
        } catch (error) {
            console.error('Error sending request:', error);
            const errorEmbed = new EmbedBuilder()
                .setColor(0xff0000) // Red for error
                .setTitle('Error')
                .setDescription('I am dead...');
            message.channel.send({ embeds: [errorEmbed] });
        }
    }
});

//Start of D&D

client.on('messageCreate', (message) => {
    // Check if the message is the !d&d roll command
    if (message.content === '!d&d roll') {
        // Roll a dice (e.g., 20-sided for D&D)
        const diceRoll = Math.floor(Math.random() * 20) + 1;

        // Send the result to the channel
        message.channel.send(`🎲 You rolled a ${diceRoll}, <@${message.author.id}>!`);
    }
    
    // Respond to the basic !d&d command
    if (message.content === '!d&d') {
        message.channel.send('I only have !d&d roll... DON\'T THINK ABOUT USING !d&d rizz');
    }/*
    if (message.content === '!d&d rizz') {
        message.channel.send('@admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin MUTE HIM');
    }*/
    if (message.content === '!dnd') {
        message.channel.send('!d&d')
    }/*
    if (message.content === '!d&d surrender'){
        message.channel.send('your ded lololololololololol')
    }*/
});

//Start of BlackJack

const cooldowns = new Map(); // This will store the cooldowns for each user

// Function to deal a random card
function getCard() {
    const cardValues = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
    const cardSuits = ['♠', '♥', '♦', '♣'];
    const value = cardValues[Math.floor(Math.random() * cardValues.length)];
    const suit = cardSuits[Math.floor(Math.random() * cardSuits.length)];
    return { value, suit };
}

// Function to calculate the total score of a hand
function calculateScore(hand) {
    let total = 0;
    let aceCount = 0;
    
    hand.forEach(card => {
        if (['J', 'Q', 'K'].includes(card.value)) {
            total += 10;
        } else if (card.value === 'A') {
            total += 11;
            aceCount++;
        } else {
            total += parseInt(card.value);
        }
    });

    // Adjust for aces if total > 21
    while (total > 21 && aceCount > 0) {
        total -= 10;
        aceCount--;
    }
    
    return total;
}

// Function to create the game embed (for ongoing game)
function createGameEmbed(playerHand, dealerHand, isDealerTurn = false) {
    const playerScore = calculateScore(playerHand);
    const dealerScore = isDealerTurn ? calculateScore(dealerHand) : '???';
    const dealerCards = isDealerTurn ? dealerHand.map(card => `${card.value}${card.suit}`).join(' ') : `${dealerHand[0].value}${dealerHand[0].suit} ??`;

    const embed = new EmbedBuilder()
        .setColor('#0099ff')
        .setTitle('Blackjack')
        .setDescription(`Try to get as close to 21 as possible without going over!`)
        .addFields(
            { name: 'Your Hand', value: playerHand.map(card => `${card.value}${card.suit}`).join(' '), inline: true },
            { name: 'Your Score', value: playerScore.toString(), inline: true },
            { name: 'Dealer\'s Hand', value: dealerCards, inline: true },
            { name: 'Dealer\'s Score', value: dealerScore.toString(), inline: true }
        )
        .setFooter({ text: 'Use the buttons below to hit, stand, or forfeit.' });

    return embed;
}

// Function to create the result embed (after game ends)
function createResultEmbed(playerScore, dealerScore, result) {
    const embed = new EmbedBuilder()
        .setColor(result === 'win' ? '#00ff00' : result === 'tie' ? '#ffff00' : '#ff0000')
        .setTitle(result === 'win' ? 'You Win!' : result === 'tie' ? 'It\'s a Tie!' : 'Dealer Wins')
        .setDescription(result === 'win' ? 'Congratulations, you beat the dealer!' : result === 'tie' ? 'You tied with the dealer.' : 'The dealer beat you. Better luck next time!')
        .addFields(
            { name: 'Your Score', value: playerScore.toString(), inline: true },
            { name: 'Dealer\'s Score', value: dealerScore.toString(), inline: true }
        );

    return embed;
}

// Function to handle the blackjack game
async function startBlackjackGame(message) {
    const playerHand = [getCard(), getCard()];
    const dealerHand = [getCard(), getCard()];

    const playerScore = calculateScore(playerHand);
    const dealerScore = calculateScore(dealerHand);

    // Check if either player or dealer starts with 21
    if (playerScore === 21 || dealerScore === 21) {
        let resultEmbed;
        if (playerScore === 21 && dealerScore === 21) {
            // Both player and dealer have 21 - it's a tie
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'tie');
        } else if (playerScore === 21) {
            // Player wins instantly
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'win');
        } else {
            // Dealer wins instantly
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'lose');
        }
        return message.channel.send({ embeds: [resultEmbed] });
    }

    const initialEmbed = createGameEmbed(playerHand, dealerHand);
    
    // Create the buttons
    const row = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder().setCustomId('hit').setLabel('Hit').setStyle(ButtonStyle.Primary),
            new ButtonBuilder().setCustomId('stand').setLabel('Stand').setStyle(ButtonStyle.Success),
            new ButtonBuilder().setCustomId('forfeit').setLabel('Forfeit').setStyle(ButtonStyle.Danger)
        );

    const gameMessage = await message.channel.send({ embeds: [initialEmbed], components: [row] });

    const collector = gameMessage.createMessageComponentCollector({ componentType: ComponentType.Button, time: 60000 });

    collector.on('collect', async (buttonInteraction) => {
        if (buttonInteraction.user.id !== message.author.id) {
            return buttonInteraction.reply({ content: 'This is not your game!', ephemeral: true });
        }

        if (buttonInteraction.customId === 'hit') {
            playerHand.push(getCard());

            if (calculateScore(playerHand) > 21) {
                // Player busts
                collector.stop('bust');
            } else {
                const updatedEmbed = createGameEmbed(playerHand, dealerHand);
                await buttonInteraction.update({ embeds: [updatedEmbed], components: [row] });
            }
        } else if (buttonInteraction.customId === 'stand') {
            // Dealer's turn
            while (calculateScore(dealerHand) < 17) {
                dealerHand.push(getCard());
            }
            collector.stop('stand');
        } else if (buttonInteraction.customId === 'forfeit') {
            collector.stop('forfeit');
        }
    });

    collector.on('end', async (collected, reason) => {
        const finalPlayerScore = calculateScore(playerHand);
        const finalDealerScore = calculateScore(dealerHand);
        let resultEmbed;

        if (reason === 'bust') {
            resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'lose');
            resultEmbed.setDescription('You busted! Dealer wins.');
        } else if (reason === 'stand') {
            if (finalDealerScore > 21 || finalPlayerScore > finalDealerScore) {
                resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'win');
            } else if (finalPlayerScore === finalDealerScore) {
                resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'tie');
            } else {
                resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'lose');
            }
        } else if (reason === 'forfeit') {
            resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'lose');
            resultEmbed.setDescription('You forfeited the game.');
        }

        await gameMessage.edit({ embeds: [resultEmbed], components: [] });
    });
}

// Function to check cooldown and show countdown in an embed
function isOnCooldown(userId, message) {
    const now = Date.now();
    const cooldown = cooldowns.get(userId);

    if (cooldown && now < cooldown) {
        const remainingTime = Math.floor((cooldown - now) / 1000);
        const cooldownTimestamp = Math.floor(cooldown / 1000); // Discord uses seconds for timestamps
        
        // Embed showing cooldown with countdown
        const cooldownEmbed = new EmbedBuilder()
            .setColor('#ff0000')
            .setTitle('Cooldown Active')
            .setDescription(`You are on cooldown. You can start a new game <t:${cooldownTimestamp}:R> (in about ${remainingTime} seconds).`);
        
        message.reply({ embeds: [cooldownEmbed] });
        return true;
    }

    // Set new cooldown
    cooldowns.set(userId, now + 10000); // 10 seconds cooldown
    return false;
}

// Listen for the message "!blackjack" to start the game
client.on('messageCreate', async (message) => {
    if (message.content === '!blackjack' || message.content === '!bj') {
        if (isOnCooldown(message.author.id, message)) {
            return; // Don't start the game if on cooldown
        }

        await startBlackjackGame(message);
    }
});

//End of BlackJack

// Cooldown map for HighLow
const highLowCooldown = new Map();

// Function to start the HighLow game
async function startHighLowGame(message) {
    const userId = message.author.id;
    const cooldownTime = 10 * 1000; // 10 seconds cooldown
    const now = Date.now();

    if (highLowCooldown.has(userId)) {
        const expirationTime = highLowCooldown.get(userId) + cooldownTime;

        if (now < expirationTime) {
            const remainingTime = Math.floor((expirationTime - now) / 1000);

            // Cooldown embed
            const cooldownEmbed = new EmbedBuilder()
                .setColor('#ffcc00')
                .setTitle('Cooldown Active')
                .setDescription(`Please wait **<t:${Math.floor(expirationTime / 1000)}:R>** before starting a new HighLow game.`)
                .setFooter({ text: 'Try again later!' });

            return message.channel.send({ embeds: [cooldownEmbed] });
        }
    }

    // Set the cooldown timestamp for the user
    highLowCooldown.set(userId, now);

    let currentNumber = Math.floor(Math.random() * 100) + 1; // Random number between 1 and 100
    const initialEmbed = new EmbedBuilder()
        .setColor('#0099ff')
        .setTitle('HighLow Game')
        .setDescription(`The current number is **${currentNumber}**. Do you think the next number will be higher or lower?`)
        .addFields(
            { name: 'Instructions', value: 'Use the buttons below to choose whether the next number will be higher or lower.' }
        );

    // Create the buttons
    const row = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder().setCustomId('higher').setLabel('Higher').setStyle(ButtonStyle.Primary),
            new ButtonBuilder().setCustomId('lower').setLabel('Lower').setStyle(ButtonStyle.Danger)
        );

    const gameMessage = await message.channel.send({ embeds: [initialEmbed], components: [row] });

    const collector = gameMessage.createMessageComponentCollector({ componentType: ComponentType.Button, time: 30000 });

    collector.on('collect', async (buttonInteraction) => {
        if (buttonInteraction.user.id !== message.author.id) {
            return buttonInteraction.reply({ content: 'This is not your game!', ephemeral: true });
        }

        const nextNumber = Math.floor(Math.random() * 100) + 1;
        let resultEmbed;

        if (buttonInteraction.customId === 'higher') {
            if (nextNumber > currentNumber) {
                resultEmbed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('You Win!')
                    .setDescription(`The next number was **${nextNumber}**. You guessed correctly!`);
            } else {
                resultEmbed = new EmbedBuilder()
                    .setColor('#ff0000')
                    .setTitle('You Lose!')
                    .setDescription(`The next number was **${nextNumber}**. You guessed wrong.`);
            }
        } else if (buttonInteraction.customId === 'lower') {
            if (nextNumber < currentNumber) {
                resultEmbed = new EmbedBuilder()
                    .setColor('#00ff00')
                    .setTitle('You Win!')
                    .setDescription(`The next number was **${nextNumber}**. You guessed correctly!`);
            } else {
                resultEmbed = new EmbedBuilder()
                    .setColor('#ff0000')
                    .setTitle('You Lose!')
                    .setDescription(`The next number was **${nextNumber}**. You guessed wrong.`);
            }
        }

        await buttonInteraction.update({ embeds: [resultEmbed], components: [] });
        collector.stop(); // Stop the collector after the interaction
    });

    collector.on('end', async (collected, reason) => {
        if (reason === 'time') {
            const timeoutEmbed = new EmbedBuilder()
                .setColor('#ff0000')
                .setTitle('Game Over')
                .setDescription('You took too long to respond! The game has ended.');

            await gameMessage.edit({ embeds: [timeoutEmbed], components: [] });
        }
    });
}

// Listen for the message "!highlow" to start the HighLow game
client.on('messageCreate', async (message) => {
    if (message.content === '!highlow') {
        await startHighLowGame(message);
    }
    if (message.content === '!hl') {
        await startHighLowGame(message);
    }
});

//End of HighLow

//Start of RPS
// Rock, Paper, Scissors Game Logic
async function startRPSGame(message) {
    const choices = ['rock', 'paper', 'scissors'];

    // Send a prompt to the user to choose rock, paper, or scissors
    const promptEmbed = new EmbedBuilder()
        .setTitle('Rock, Paper, Scissors')
        .setDescription('Type "rock", "paper", or "scissors" to make your choice!')
        .setColor(0x00FF00);

    await message.channel.send({ embeds: [promptEmbed] });

    // Collect user's choice
    const filter = (response) => {
        return choices.includes(response.content.toLowerCase()) && response.author.id === message.author.id;
    };

    // Wait for the user to reply with a valid choice (rock, paper, or scissors)
    try {
        const collected = await message.channel.awaitMessages({ filter, max: 1, time: 30000, errors: ['time'] });
        const userChoice = collected.first().content.toLowerCase();
        const botChoice = choices[Math.floor(Math.random() * choices.length)];

        // Determine the result
        let result;
        if (userChoice === botChoice) {
            result = "It's a tie!";
        } else if (
            (userChoice === 'rock' && botChoice === 'scissors') ||
            (userChoice === 'paper' && botChoice === 'rock') ||
            (userChoice === 'scissors' && botChoice === 'paper')
        ) {
            result = 'You win!';
        } else {
            result = 'You lose!';
        }

        // Send the result embed
        const resultEmbed = new EmbedBuilder()
            .setTitle('Rock, Paper, Scissors')
            .setDescription(`You chose **${userChoice}**.\nThe bot chose **${botChoice}**.\n${result}`)
            .setColor(0x00FF00);

        await message.channel.send({ embeds: [resultEmbed] });

    } catch (err) {
        // Handle the case where the user didn't reply in time
        await message.channel.send('You did not choose in time! Please try again.');
    }
}

// Listen for the message "!rockpaperscissors" or "!rps" to start the game
client.on('messageCreate', async (message) => {
    if (message.content === '!rockpaperscissors' || message.content === '!rps') {
        await startRPSGame(message);
    }
});

//End of RPS

//Start of Tic-Tac-Toe

// Function to create a Tic-Tac-Toe board
function createTicTacToeBoard(board) {
    let display = '';
    for (let i = 0; i < board.length; i++) {
        display += board[i] === null ? `⬜` : board[i] === 'X' ? '❌' : '⭕';
        if ((i + 1) % 3 === 0) display += '\n';
    }
    return display;
}

// Function to check for a winner
function checkWinner(board) {
    const winningPatterns = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], // Horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8], // Vertical
        [0, 4, 8], [2, 4, 6]             // Diagonal
    ];

    for (const pattern of winningPatterns) {
        const [a, b, c] = pattern;
        if (board[a] && board[a] === board[b] && board[a] === board[c]) {
            return board[a]; // Return 'X' or 'O' if there's a winner
        }
    }

    return null; // No winner yet
}

// Function to create buttons for each cell
function createBoardButtons(board) {
    const actionRows = [];
    for (let i = 0; i < 3; i++) {
        const row = new ActionRowBuilder();
        for (let j = 0; j < 3; j++) {
            const index = i * 3 + j;
            row.addComponents(
                new ButtonBuilder()
                    .setCustomId(index.toString()) // Unique ID for each button (0 to 8)
                    .setLabel(board[index] ? (board[index] === 'X' ? '❌' : '⭕') : '⬜') // Show X, O, or empty
                    .setStyle(ButtonStyle.Secondary)
                    .setDisabled(!!board[index]) // Disable button if the cell is already occupied
            );
        }
        actionRows.push(row);
    }
    return actionRows;
}

// Function to start a Tic-Tac-Toe game against another user or bot
async function startTicTacToe(message, mode) {
    const board = Array(9).fill(null); // Create an empty Tic-Tac-Toe board
    let currentPlayer = 'X'; // X always goes first
    let gameOver = false; // Track if game is over

    // Embed to display the Tic-Tac-Toe game
    const embed = new EmbedBuilder()
        .setTitle('Tic-Tac-Toe')
        .setDescription(`It's ${currentPlayer}'s turn.`)
        .setColor(0x00FF00); // Initial color is green for ongoing game

    const gameMessage = await message.channel.send({ embeds: [embed], components: createBoardButtons(board) });

    // Function to update the game board
    async function updateGameBoard(index) {
        if (gameOver || board[index]) return;

        board[index] = currentPlayer;
        const winner = checkWinner(board);

        if (winner) {
            gameOver = true;
            embed.setDescription(createTicTacToeBoard(board))
                .setFooter({ text: `${winner} wins!` })
                .setColor(winner === 'X' ? 0x00FF00 : 0xFF0000); // Green for win, Red for loss
            await gameMessage.edit({ embeds: [embed], components: [] });
            return;
        }

        if (board.every(cell => cell !== null)) {
            gameOver = true;
            embed.setDescription(createTicTacToeBoard(board))
                .setFooter({ text: 'It\'s a tie!' })
                .setColor(0xFFFF00); // Yellow for tie
            await gameMessage.edit({ embeds: [embed], components: [] });
            return;
        }

        currentPlayer = currentPlayer === 'X' ? 'O' : 'X'; // Switch turns
        embed.setDescription(createTicTacToeBoard(board))
            .setFooter({ text: `Current Player: ${currentPlayer}` });

        await gameMessage.edit({ embeds: [embed], components: createBoardButtons(board) }); // Update buttons

        if (mode === 'bot' && currentPlayer === 'O') {
            const botMove = board.indexOf(null);
            await updateGameBoard(botMove); // Bot moves in the first available spot
        }
    }

    // Create a button collector to listen for user moves
    const collector = gameMessage.createMessageComponentCollector({ time: 60000 });

    collector.on('collect', async (interaction) => {
        const index = parseInt(interaction.customId); // Get button ID (cell index)
        if (!board[index] && !gameOver) {
            await updateGameBoard(index);
        }
        await interaction.deferUpdate(); // Acknowledge the button click
    });

    // Handle timeout
    collector.on('end', async () => {
        if (!gameOver) { // Only show timeout message if the game wasn't already finished
            embed.setFooter({ text: 'Game ended due to inactivity.' });
            await gameMessage.edit({ embeds: [embed], components: [] }); // Disable all buttons
        }
    });
}

// Function to show game mode selection
async function selectTicTacToeMode(message) {
    const modeEmbed = new EmbedBuilder()
        .setTitle('Tic-Tac-Toe')
        .setDescription('Select the game mode:\n- Play against another user\n- Play against the bot')
        .setColor(0x00FF00);

    const buttons = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder()
                .setCustomId('play_with_user')
                .setLabel('Play with Another User')
                .setStyle(ButtonStyle.Primary),
            new ButtonBuilder()
                .setCustomId('play_with_bot')
                .setLabel('Play against the Bot')
                .setStyle(ButtonStyle.Secondary)
        );

    const modeMessage = await message.channel.send({ embeds: [modeEmbed], components: [buttons] });

    // Create a collector to listen for button clicks
    const collector = modeMessage.createMessageComponentCollector({ time: 30000 });

    collector.on('collect', async (interaction) => {
        if (interaction.customId === 'play_with_user') {
            await interaction.update({ embeds: [new EmbedBuilder().setTitle('Starting a game with another user...').setColor(0x00FF00)], components: [] });
            await startTicTacToe(message, 'user');
        } else if (interaction.customId === 'play_with_bot') {
            await interaction.update({ embeds: [new EmbedBuilder().setTitle('Starting a game against the bot...').setColor(0x00FF00)], components: [] });
            await startTicTacToe(message, 'bot');
        }
    });

    // Handle timeout
    collector.on('end', async () => {
        await modeMessage.edit({ embeds: [new EmbedBuilder().setTitle('No selection made. Game cancelled.').setColor(0xFF0000)], components: [] });
    });
}

// Listen for the message "!tictactoe" or "!ttt" to start the game
client.on('messageCreate', async (message) => {
    if (message.content === '!tictactoe' || message.content === '!ttt') {
        await selectTicTacToeMode(message);
    }
});

//End of Tic-Tac-Toe

//Start of Coin Flip

// Coin Flip Game Logic
async function startCoinFlipGame(message) {
    const outcomes = ['Heads', 'Tails'];
    const result = outcomes[Math.floor(Math.random() * outcomes.length)];

    const coinFlipEmbed = new EmbedBuilder()
        .setTitle('Coin Flip')
        .setDescription(`The coin landed on **${result}**!`)
        .setColor(0x00FF00);

    await message.channel.send({ embeds: [coinFlipEmbed] });
}

// Listen for the message "!coinflip" or "!cf" to start the game
client.on('messageCreate', async (message) => {
    if (message.content === '!coinflip' || message.content === '!cf') {
        await startCoinFlipGame(message);
    }
});

//End of Coin Flip


//Start of Trivia Quiz

// Function to fetch a random trivia question with a specific category
async function fetchTriviaQuestion(category = null) {
    try {
        const categoryQuery = category ? `&category=${category}` : '';
        const response = await axios.get(`https://opentdb.com/api.php?amount=1&type=multiple${categoryQuery}`);
        const triviaData = response.data.results[0];

        // Decode HTML entities in the question and answers
        const question = he.decode(triviaData.question);
        const options = [...triviaData.incorrect_answers, triviaData.correct_answer].map(answer => he.decode(answer));
        
        // Shuffle options
        options.sort(() => Math.random() - 0.5);

        return {
            question,
            options,
            answer: he.decode(triviaData.correct_answer) // Decode correct answer
        };
    } catch (error) {
        console.error('Error fetching trivia question:', error);
        return null; // Return null if an error occurs
    }
}

// Function to start the trivia game after selecting a topic
async function startTriviaGame(message, category = null) {
    const trivia = await fetchTriviaQuestion(category); // Fetch a trivia question with the selected category
    if (!trivia) {
        message.channel.send('Sorry, I could not fetch a trivia question at this time.');
        return;
    }

    const triviaEmbed = new EmbedBuilder()
        .setTitle('Trivia Quiz')
        .setDescription(trivia.question)
        .addFields(trivia.options.map((option, index) => ({ name: `Option ${String.fromCharCode(65 + index)}`, value: option })))
        .setColor(0x00FF00); // Green color for the trivia question embed

    const buttons = new ActionRowBuilder()
        .addComponents(
            ...trivia.options.map((option, index) =>
                new ButtonBuilder()
                    .setCustomId(String.fromCharCode(65 + index)) // A, B, C, D
                    .setLabel(String.fromCharCode(65 + index)) // A, B, C, D
                    .setStyle(ButtonStyle.Primary) // Correct style
            )
        );

    const triviaMessage = await message.channel.send({ embeds: [triviaEmbed], components: [buttons] });

    // Create a button collector to listen for answers
    const filter = (interaction) => interaction.user.id === message.author.id;
    const collector = triviaMessage.createMessageComponentCollector({ filter, time: 30000 }); // Timeout set to 30 seconds

    collector.on('collect', async (interaction) => {
        const userAnswer = interaction.customId; // A, B, C, D
        const userAnswerText = trivia.options[interaction.customId.charCodeAt(0) - 65]; // Get the corresponding answer option

        if (userAnswerText === trivia.answer) {
            const correctEmbed = new EmbedBuilder()
                .setTitle('Correct Answer!')
                .setDescription(`You got it right! The correct answer was: **${trivia.answer}**.`)
                .setColor(0x00FF00); // Green for correct

            await interaction.update({ embeds: [correctEmbed], components: [] });
        } else {
            const incorrectEmbed = new EmbedBuilder()
                .setTitle('Wrong Answer!')
                .setDescription(`You chose: **${userAnswerText}**\nThe correct answer was: **${trivia.answer}**.`)
                .setColor(0xFF0000); // Red for incorrect

            await interaction.update({ embeds: [incorrectEmbed], components: [] });
        }

        // Stop the collector after an answer is submitted
        collector.stop();
    });

    collector.on('end', async (collected, reason) => {
        if (reason === 'time') {
            const timeoutEmbed = new EmbedBuilder()
                .setTitle('Time is Up!')
                .setDescription('No answer was selected within the time limit.')
                .setColor(0xFFFF00); // Yellow for timeout

            await triviaMessage.edit({ embeds: [timeoutEmbed], components: [] });
        }
    });
}

// Function to select trivia category
async function selectTriviaCategory(message) {
    const categoryEmbed = new EmbedBuilder()
        .setTitle('Trivia Categories')
        .setDescription('Select a category to begin the quiz!')
        .setColor(0x00FF00);

    const categories = [
        { label: 'General Knowledge', categoryId: 9 },
        { label: 'Science', categoryId: 17 },
        { label: 'History', categoryId: 23 },
        { label: 'Sports', categoryId: 21 }
    ];

    const buttons = new ActionRowBuilder()
        .addComponents(
            categories.map(cat =>
                new ButtonBuilder()
                    .setCustomId(cat.categoryId.toString())
                    .setLabel(cat.label)
                    .setStyle(ButtonStyle.Primary)
            )
        );

    const categoryMessage = await message.channel.send({ embeds: [categoryEmbed], components: [buttons] });

    // Create a collector to handle category selection
    const filter = (interaction) => interaction.user.id === message.author.id;
    const collector = categoryMessage.createMessageComponentCollector({ filter, time: 30000 });

    collector.on('collect', async (interaction) => {
        const selectedCategory = interaction.customId;
        await interaction.update({ content: `Category selected: ${categories.find(cat => cat.categoryId.toString() === selectedCategory).label}`, components: [] });
        await startTriviaGame(message, selectedCategory);
    });

    collector.on('end', async (collected, reason) => {
        if (reason === 'time') {
            await categoryMessage.edit({ content: 'No category selected. Game cancelled.', components: [] });
        }
    });
}

// Listen for the message "!trivia" or "!quiz" to start the game
client.on('messageCreate', async (message) => {
    if (message.content === '!trivia' || message.content === '!quiz') {
        await selectTriviaCategory(message);
    }
});

//End of Trivia Quiz

//Start of AFK

// Function to format time in the "X hours Y minutes and Z seconds" style
function formatAFKDuration(duration) {
    const days = Math.floor(duration / (24 * 60 * 60));
    const hours = Math.floor((duration % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((duration % (60 * 60)) / 60);
    const seconds = duration % 60;

    let formattedTime = '';

    if (days > 0) {
        formattedTime += `${days} day${days === 1 ? '' : 's'}`;
    }
    if (hours > 0) {
        if (formattedTime) formattedTime += ', ';
        formattedTime += `${hours} hour${hours === 1 ? '' : 's'}`;
    }
    if (minutes > 0) {
        if (formattedTime) formattedTime += ', ';
        formattedTime += `${minutes} minute${minutes === 1 ? '' : 's'}`;
    }
    if (seconds > 0 || (!days && !hours && !minutes)) { // Show seconds even if they're the only value
        if (formattedTime) formattedTime += ' and ';
        formattedTime += `${seconds} second${seconds === 1 ? '' : 's'}`;
    }

    return formattedTime;
}

client.on('messageCreate', async (message) => {
    const userId = message.author.id;
    const guildId = message.guild.id;

    // Ensure afkUsers map has a sub-map for each guild
    if (!afkUsers.has(guildId)) {
        afkUsers.set(guildId, new Map());
    }
    const guildAfkUsers = afkUsers.get(guildId);

    // If the user is AFK and sends a message, remove AFK status
    if (guildAfkUsers.has(userId)) {
        const afkInfo = guildAfkUsers.get(userId);
        const afkDuration = Math.floor((Date.now() - afkInfo.timestamp) / 1000); // Duration in seconds
        guildAfkUsers.delete(userId);

        const formattedDuration = formatAFKDuration(afkDuration);

        const returnEmbed = new EmbedBuilder()
            .setColor('#00ff00')
            .setTitle('Welcome Back!')
            .setDescription(`You were AFK for **${formattedDuration}**.`);

        const returnMessage = await message.channel.send({ embeds: [returnEmbed] });

        // Delete the return message after 10 seconds
        setTimeout(() => {
            returnMessage.delete().catch(console.error); // Handle message deletion errors if any
        }, 10000);

        return;
    }

    // Handle !afk command
    if (message.content.startsWith('!afk')) {
        const afkMessage = message.content.split(' ').slice(1).join(' ') || 'AFK';
        guildAfkUsers.set(userId, { message: afkMessage, timestamp: Date.now() });

        const afkEmbed = new EmbedBuilder()
            .setColor('#ffcc00')
            .setTitle('AFK Status Set')
            .setDescription(`You are now AFK: **${afkMessage}**.\nYou will be marked as AFK until you send a message.`);

        return message.channel.send({ embeds: [afkEmbed] });
    }

    // Check if mentioned users are AFK
    const mentionedUsers = message.mentions.users;
    mentionedUsers.forEach((mentionedUser) => {
        if (guildAfkUsers.has(mentionedUser.id)) {
            const afkInfo = guildAfkUsers.get(mentionedUser.id);

            const afkMentionEmbed = new EmbedBuilder()
                .setColor('#ff0000')
                .setTitle('User is AFK')
                .setDescription(`${mentionedUser.username} is currently AFK: **${afkInfo.message}**.`);

            return message.channel.send({ embeds: [afkMentionEmbed] });
        }
    });

});

//End of AFK

/*
client.on(Events.MessageCreate, (message) => {
    // Define the set of users allowed to use this command (replace with actual user IDs)
    const allowedUsers = ['435125886996709377', '1286383453016686705']; // Add allowed user IDs here

    // Check if the message starts with the specific command
    if (message.content.startsWith('!aetherx news')) {
        // Check if the message author is in the allowedUsers array
        if (allowedUsers.includes(message.author.id)) {
            // Get the message content after the command
            const userMessage = message.content.slice('!aetherx news'.length).trim();

            // Check if the user provided a message
            if (!userMessage) {
                return message.channel.send('Please provide a message to send.');
            }

            // Create an embed
            const embed = new EmbedBuilder()
                .setTitle('AetherX News Update')
                .setDescription(userMessage)
                .setColor('#0099ff')  // You can change the color
                .setTimestamp()
                .setFooter({ text: 'AetherX News Bot', iconURL: 'https://i.imgur.com/AfFp7pu.png' }); // Optional footer and icon

            // Define your designated channel ID
            const designatedChannelId = '1291076103628390442'; // Replace with the actual channel ID

            // Get the designated channel
            const designatedChannel = client.channels.cache.get(designatedChannelId);
            if (designatedChannel) {
                // Send the embed and mention @AetherX News (replace with the correct role ID)
                designatedChannel.send({
                    content: '<@&1291074211904749658>',  // Replace with actual role ID for @AetherX News
                    embeds: [embed],
                });
            } else {
                message.channel.send('Designated channel not found.');
            }
        } else {
            // Notify the user they don't have permission to use the command
            message.channel.send('You do not have permission to use this command.');
        }
    }
});
*/
client.login(process.env.BOT_TOKEN);
