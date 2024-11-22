// Import the necessary modules
require('dotenv').config();
const { Client, GatewayIntentBits, ButtonBuilder, ButtonStyle, ActionRowBuilder, EmbedBuilder, ComponentType, Events, Intents, interactionCreate, StringSelectMenuBuilder, AttachmentBuilder, Partials, ActivityType } = require('discord.js');
const schedule = require('node-schedule');
const spotifyClientId = process.env.SPOTIFY_CLIENT_ID;
const spotifyClientSecret = process.env.SPOTIFY_CLIENT_SECRET;
const youtubeApiKey = process.env.YOUTUBE_API_KEY;
/*const WORDNIK_API_KEY = process.env.WORDNIK_API_KEY;*/ //This will be enabled for testing once the API key arrives (ETA: Unknown)
const notificationConfig = require('./notifications.json');
const { token, clientId, guildId } = require('./config.json');
const { DisTube } = require('distube');
const { YtDlpPlugin } = require('@distube/yt-dlp');
const { SpotifyPlugin } = require('@distube/spotify');
const axios = require('axios');
const { REST } = require('@discordjs/rest');
const { Routes } = require('discord-api-types/v10');
const isTestMode = false; // Change to false when not in test mode
const afkUsers = new Map();
const he = require('he');
const fs = require('fs');
const path = require('path');
//const { Routes } = require('discord-api-types/v9');
const rest = new REST({ version: '10' }).setToken(token);
const dotenv = require('dotenv');
const EventEmitter = require('events');
const emitter = new EventEmitter();
// Axios instance for StartGG API
const startGGAPI = axios.create({
    baseURL: 'https://api.start.gg/gql/alpha',
    headers: { 'Authorization': `Bearer ${process.env.STARTGG_API_KEY}` }
  });
  
  // Read the file containing user details in the new format
  const userDetailsPath = path.join(__dirname, 'other', 'allowed.txt');
  const userDetails = fs.readFileSync(userDetailsPath, 'utf-8')
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0); // Remove empty lines or whitespace
  
  // Objects to hold user-specific data
  const userColors = {};
  const userColorsN = {};
  const allowedUsers = [];
  const ownerUsers = [];
  
  // Parse the file into userColors, userColorsN, allowedUsers, and ownerUsers
  let currentUserId = null;
  
  userDetails.forEach(line => {
      if (!line.startsWith('-')) {
          // A new UserID entry
          currentUserId = line;
          allowedUsers.push(currentUserId); // Add to allowed users by default
      } else if (currentUserId) {
          // Process details under the current UserID
          const [key, value] = line.slice(1).split('=').map(part => part.trim());
  
          if (key === 'Hexcode') {
              userColorsN[currentUserId] = value;
          } else if (key === 'ANSIcode') {
              userColors[currentUserId] = value;
          } else if (key === 'Owner' && value.toLowerCase() === 'true') {
              ownerUsers.push(currentUserId);
          }
      }
  });
  
  console.log('Allowed users:', allowedUsers);
  console.log('Owners:', ownerUsers);
  console.log('ANSI colors:', userColors);
  console.log('Hex colors:', userColorsN);  
const designatedChannelId = '1067445342683005050'; // Replace with the actual channel ID
const designatedChannel = client.channels.cache.get(designatedChannelId);
// const trustUsers = ['userid'];
// const level1allow = [...trustUsers, ...allowedUsers];
// Group end
const { SlashCommandBuilder } = require('@discordjs/builders');

// Create a new Discord client with intents to listen for messages
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.DirectMessages,
        GatewayIntentBits.GuildPresences,
    ],
    partials: [Partials.Channel] // Required for DM support
});

// Logging for any errors that are not caught in the terminal
process.on('unhandledRejection', (error) => {
    console.error('Unhandled promise rejection:', error);
});

client.on('error', (error) => {
    console.error('Client error:', error);
});

// Function to log errors to error.log
function logError(error) {
    const errorMessage = `[${new Date().toISOString()}] ${error}\n`;
    fs.appendFileSync('./error.log', errorMessage, 'utf8');
}

// Capture console errors
console.error = (function(oldError) {
    return function(...args) {
        logError(args.join(' '));
        oldError.apply(console, args);
    };
})(console.error);

// Capture unhandled promise rejections
process.on('unhandledRejection', (reason) => {
    logError(`Unhandled Rejection: ${reason}`);
});

// Capture uncaught exceptions
process.on('uncaughtException', (err) => {
    logError(`Uncaught Exception: ${err}`);
    process.exit(1); // Optional: Exit the process after logging the error
});

//MaxListeners
emitter.setMaxListeners(30)

/*await rest.put(
    Routes.applicationCommands(client.user.id),
    { body: commands }  // This will now include both the 'about' and 'ban' commands
);*/

// Load environment variables from .env file
require('dotenv').config(); // Ensure dotenv is required correctly

// Import your command files
const aboutCommand = require('./commands/about.js');
const banCommand = require('./commands/ban.js');
const kickCommand = require('./commands/kick.js');
const muteCommand = require('./commands/mute.js');
const unmuteCommand = require('./commands/unmute.js');
const timeoutCommand = require('./commands/timeout.js');
const sayCommand = require('./commands/say.js');
const pingCommand = require('./commands/ping.js');
const uptimeCommand = require('./commands/uptime.js');
const setStatusCommand = require('./commands/setstatus.js');
const remindCommand = require('./commands/reminder.js');

// Build the commands array for registration
const commands = [
    aboutCommand.data.toJSON(),
    banCommand.data.toJSON(),
    kickCommand.data.toJSON(),
    muteCommand.data.toJSON(),
    unmuteCommand.data.toJSON(),
    timeoutCommand.data.toJSON(),
    sayCommand.data.toJSON(),
    pingCommand.data.toJSON(),
    uptimeCommand.data.toJSON(),
    setStatusCommand.data.toJSON(),
    remindCommand.data.toJSON(),
];

// Now, you can use this 'commands' array to register your commands with Discord

//Spofiy Log
console.log(`Spotify Client ID: ${spotifyClientId}`);
console.log(`Spotify Client Secret: ${spotifyClientSecret}`);

// Register the slash commands when the bot is ready
client.once('ready', async () => {
    try {
        console.log('\x1b[36m%s\x1b[0m', 'Bot is online and ready for war with Discord users!');

        // Register slash commands globally
        await rest.put(
            Routes.applicationCommands(client.user.id),
            { body: commands }
        );
        console.log('\x1b[32m%s\x1b[0m', 'Slash commands registered successfully.');
    } catch (error) {
        console.error('\x1b[31m%s\x1b[0m', 'Error during bot setup:', error);
    }
    if (isTestMode) {
        console.warn(`\"You have test mode set to \'true\', set it to \'false\' when you are done testing it!\" -Lucas \（・ω‐\）`);
    }
    console.log('\x1b[34m%s\x1b[0m', '\"Make sure to use clear when you\'re done!\" -Lucas \（・ω‐\）');

    client.on('interactionCreate', async interaction => {
        if (!interaction.isCommand()) return; // Make sure it's a slash command
      
        const { commandName } = interaction;
      
        // Find and execute the corresponding command
        if (commandName === 'about') {
            await aboutCommand.execute(interaction);
        } else if (commandName === 'ban') {
            await banCommand.execute(interaction);
        } else if (commandName === 'kick') {
            await kickCommand.execute(interaction);
        } else if (commandName === 'mute') {
            await muteCommand.execute(interaction);
        } else if (commandName === 'unmute') {
            await unmuteCommand.execute(interaction);
        } else if (commandName === 'timeout') {
            await timeoutCommand.execute(interaction);
        } else if (commandName === 'say') {
            await sayCommand.execute(interaction);
        } else if (commandName === 'ping') {
            await pingCommand.execute(interaction);
        } else if (commandName === 'uptime') {
            await uptimeCommand.execute(interaction);
        } else if (commandName === 'setstatus') {
            await setStatusCommand.execute(interaction);
        } else if (commandName === 'remind') {
            await remindCommand.execute(interaction);
        }
    });
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


// Handle inwarneractionCreate event for slash commands
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isCommand()) return;

    const { commandName } = interaction;

    if (commandName === 'about') {
        const aboutEmbed = new EmbedBuilder()
            .setColor(0x7289da) // Discord's blurple color
            .setTitle('AetherX Bot Information')
            .setDescription('AetherX is a custom Discord bot designed by Androgalaxi and lmutt090.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8) or the link below.')
            .addFields(
                { name: 'Developer', value: '[Androgalaxi](https://discord.com/users/435125886996709377) and [lmutt090](https://discord.com/users/1286383453016686705)' },
                { name: 'Bot Version', value: '0.3' },
                { name: 'Bot Invite Link', value: '[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8)' },
                { name: 'Support Server', value: '[Join the Support Server](https://discord.gg/yFY8Fnbtp9)' }
            )
            .setFooter({ text: 'AetherX Bot - Created with suffering by Androgalaxi and lmutt090' });

        await interaction.reply({ embeds: [aboutEmbed] });
    }
});

//Auto Restart Config | DO NOT TOUCH
// Load restart.json
/* const config = JSON.parse(fs.readFileSync('restart.json', 'utf8'));

// Schedule restarts for each specified time
config.restartTimes.forEach(time => {
    schedule.scheduleJob(time, () => {
        console.log("Restarting bot...");
        process.exit(0); // Exit to trigger the PM2 restart
    });
});

console.log("Restart schedules loaded:", config.restartTimes);

*/
// Your Giphy API Key
const GIPHY_API_KEY = process.env.GIPHY_API_KEY;

client.once('ready', () => {
    console.log(`Logged in as ${client.user.tag}`);
});

function logErrorToFile(error) {
    const errorMessage = `[${new Date().toISOString()}] ${error}\n`;
    fs.appendFile('error.log', errorMessage, (err) => {
        if (err) console.error('Failed to write to log file:', err);
    });
}

client.on('messageCreate', async (message) => {
    if (message.author.bot || !message.content.startsWith('!gif')) return;

    const query = message.content.split(' ').slice(1).join(' ');
    if (!query) {
        return message.channel.send('Please provide a search term after the command (e.g., `!gif happy`).');
    }

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
            return message.channel.send('No GIFs found for that search term.');
        }

        const gifUrl = response.data.data[0].images.original.url;
        console.log('Fetched GIF URL:', gifUrl);

        // Path to the Giphy watermark GIF file
        const footerGifPath = path.join('H:', 'Giphy Attribution Marks', 'Animated Logos', 'PoweredBy_200_Horizontal_Light-Backgrounds_With_Logo.gif');
        const footerGifAttachment = new MessageAttachment(footerGifPath, 'GiphyWatermark.gif');

        const embed = new MessageEmbed()
            .setColor(0x0099ff)
            .setTitle(`Here's a GIF for: ${query}`)
            .setImage(gifUrl)
            .setFooter('Powered by Giphy', 'attachment://GiphyWatermark.gif');

        await message.channel.send({
            embeds: [embed],
            files: [footerGifAttachment]
        });

        setTimeout(() => {
            message.delete().catch(console.error);
        }, 5000);

    } catch (error) {
        console.error('Error in messageCreate event:', error);
        logErrorToFile(error);
        message.channel.send('An error occurred while fetching the GIF. Please try again later.');
    }
});

// Map to store the last help message for each user
const userHelpMessages = new Map();

//Server Info
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    // Check if the message starts with "!serverinfo" or "!sinfo"
    if (message.content.startsWith('!serverinfo') || message.content.startsWith('!sinfo')) {
        const { guild } = message;

        // Fetch server information
        const serverName = guild.name;
        const createdAt = Math.floor(guild.createdTimestamp / 1000);
        const memberCount = guild.memberCount;
        const roleCount = guild.roles.cache.size;
        const textChannelCount = guild.channels.cache.filter(channel => channel.type === 'GUILD_TEXT').size;
        const voiceChannelCount = guild.channels.cache.filter(channel => channel.type === 'GUILD_VOICE').size;
        const owner = await guild.fetchOwner();
        
        // Fetch owner roles and get the highest role name
        const ownerRoles = owner.roles.cache;
        const ownerRole = ownerRoles.size > 0 ? ownerRoles.sort((a, b) => b.position - a.position).first().name : 'No Role';

        // Additional details
        const boostCount = guild.premiumSubscriptionCount || 0;
        const boostTier = guild.premiumTier ? `Tier ${guild.premiumTier}` : 'None';
        const moderationLevel = guild.verificationLevel;
        const explicitContentFilter = guild.explicitContentFilter;

        // Helper function to format fields with inline code for values only
        const formatField = (label, value, useCodeBlock = true) => 
            useCodeBlock ? `${label} : \`${value}\`` : `${label} : ${value}`;

        // Create an embed with server information
        const serverEmbed = new EmbedBuilder()
            .setTitle(`Server Info - ${serverName}`)
            .setColor(0xADD8E6) // Light blue color
            .setThumbnail(guild.iconURL({ dynamic: true }))
            .addFields(
                { name: formatField('Server Name', serverName, false), value: '\u200b' },
                { name: formatField('Created On', `<t:${createdAt}:F>`, false), value: '\u200b' },
                { name: formatField('Owner', owner.user.tag, false), value: `Role: ${ownerRole}` }, // Display owner name and role
                { name: formatField('Total Members', `${memberCount}`), value: '\u200b' },
                { name: formatField('Roles', `${roleCount}`), value: '\u200b' },
                { name: formatField('Text Channels', `${textChannelCount}`), value: '\u200b' },
                { name: formatField('Voice Channels', `${voiceChannelCount}`), value: '\u200b' },
                { name: formatField('Boosts', `${boostCount} (${boostTier})`), value: '\u200b' },
                { name: formatField('Moderation Level', `${moderationLevel}`), value: '\u200b' },
                { name: formatField('Explicit Content Filter', `${explicitContentFilter}`), value: '\u200b' }
            )
            .setTimestamp();

        // Send the server information embed
        await message.channel.send({ embeds: [serverEmbed] });
    }
});

//User profile options
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    if (message.content.startsWith('!profile')) {
        const args = message.content.split(' ').slice(1);
        let targetUser;

        if (args.length === 0) {
            // No user mentioned, use the message author
            targetUser = message.author;
        } else {
            // Check if the argument is a mention or an ID
            if (message.mentions.users.size > 0) {
                targetUser = message.mentions.users.first();
            } else {
                // Try to find the user by ID
                targetUser = await client.users.fetch(args[0]).catch(() => null);
            }
        }

        if (!targetUser) {
            // Create an error embed
            const errorEmbed = new EmbedBuilder()
                .setTitle('User Not Found')
                .setDescription('Please mention a valid user or provide a valid user ID.')
                .setColor(0xFF0000); // Red color for error

            return message.channel.send({ embeds: [errorEmbed] });
        }

        // Fetch guild member to get roles and joined date
        const guildMember = message.guild.members.cache.get(targetUser.id) || await message.guild.members.fetch(targetUser.id);

        // Create a profile embed
        const profileEmbed = new EmbedBuilder()
            .setTitle(`${targetUser.username}'s Profile`)
            .setColor(0x57b9ff) // Updated color
            .addFields(
                { name: '__User Information__', value: `**User ID:** ${targetUser.id}\n—\n**Username:** ${targetUser.username}\n—\n**Is Bot:** ${targetUser.bot ? 'Yes' : 'No'}\n—\n**Created At:** <t:${Math.floor(targetUser.createdTimestamp / 1000)}:F>`, inline: false },
                { name: '__Server Information__', value: `**Joined Server:** <t:${Math.floor(guildMember.joinedTimestamp / 1000)}:F>\n—\n**Roles:** ${guildMember.roles.cache.map(role => `<@&${role.id}>`).join(', ') || 'No roles'}`, inline: false }
            )
            .setThumbnail(targetUser.displayAvatarURL());

        // Send the profile embed
        await message.channel.send({ embeds: [profileEmbed] });
    }
});

// Function to send or edit help message based on the requested page
async function sendHelpMessage(message, page = 1) { // Default page is 1
    const helpPages = [
        {
            title: 'General Commands',
            description: '!changelog - Display changes made to the bot.\n!request - Request a feature or features to be added\n!afk - Go afk and set a custom message\n!ping - Displays the bot latency and API latency.\n!help - Shows this help menu with all available commands.\n!yippie - Sends a "Yippee" GIF.\n!global [message] - Sends a message to all servers where the bot is present.\n!about or !info - Provides information about the bot, developer, and invites.\n!profile/!profile @user/!profile (user ID) - See information on a users profile.'
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
            description: '!blackjack or !bj - Play a game of BlackJack.\n!d&d - Roll the dice!\n!highlow or !hl - Play a game of HighLow\n!tictactoe or !ttt - Play a game of TicTacToe against another user or the bot\n !coinflip or !cf - Flip a coin\n!trivia or !quiz - Try to pick the correct answer on a random question\n !rockpaperscissors or !rps - Play a game of Rock Paper Scissors'
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

client.on('messageCreate', async (message) => {
    if (message.author.bot || !message.content.startsWith('!purge')) return;

    const args = message.content.split(' ').slice(1);
    const amount = parseInt(args[0]);

    if (!message.member.permissions.has('MANAGE_MESSAGES')) {
        return message.reply('You do not have permission to use this command.');
    }

    if (!amount || amount < 1 || amount > 100) {
        return message.reply('Please specify a number of messages to delete (1-100).');
    }

    try {
        const deletedMessages = await message.channel.bulkDelete(amount + 1, true);
        message.channel.send(`Deleted ${deletedMessages.size - 1} messages.`)
            .then(msg => setTimeout(() => msg.delete(), 5000));
    } catch (error) {
        console.error(error);
        message.reply('There was an error trying to purge messages in this channel.');
    }
});

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

client.on('messageCreate', async (message) => {
    if (message.content.startsWith('!log') || message.content.startsWith('Aether,') || message.content.startsWith('Log this:')) {
        // Check if the user is allowed to log
        if (!allowedUsers.includes(message.author.id)) {
            message.channel.send('You do not have permission to use this command... LOL!!!! btw, this is a dev command...');
            console.error(`${message.author.username} tried to log`);
            return;
        }

        const args = message.content.split(' ').slice(1).join(' ');

        if (!args) {
            return message.channel.send('Please provide a message to log.');
        }

        // Determine the user's prefix based on ownership
        const userPrefix = ownerUsers.includes(message.author.id) ? '(Owner)' : '(Dev)';

        // Determine the color for the log based on the user
        const userColor = userColors[message.author.id] || '\x1b[37m'; // Default to white if user not found

        // Log the message to the console with the user's color and prefix
        console.log(`${userColor}[LOG] ${userPrefix} ${message.author.username}: ${args}\x1b[37m`);

        // Send confirmation to the Discord channel
        message.channel.send('Your message has been logged to the console.');
    }
});

// Respond to specific messages
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    // Respond to !ping command and send latency
    if (message.content === '!ping') {
        const sent = Date.now();
        console.log('Bot: Pinging...')
        message.channel.send('Pinging...').then(sentMessage => {
            const timeTaken = Date.now() - sent;
            sentMessage.edit(`Pong! Latency is ${timeTaken}ms. API Latency is ${Math.round(client.ws.ping)}ms.`);
            console.log(`Latency is ${timeTaken}ms. API Latency is ${Math.round(client.ws.ping)}ms.`);
        });
    }

client.on('messageCreate', async (message) => {
    // Check if the command is `!cringeattack`
    if (message.content.startsWith('!cringeattack')) {
        // Define the path to the image file you want the bot to post
        const filePath = path.join(__dirname, 'images', 'file.gif'); // Replace 'file.gif' with the actual file name

        // Create the attachment from the file
        const file = new AttachmentBuilder(filePath);

        // Post the file in the same channel where the command was sent
        message.channel.send({ files: [file] })
            .then(() => {
                console.log(`Image posted by bot in ${message.channel.name}`);
            })
            .catch(error => {
                console.error(`Failed to post image: ${error}`);
                message.channel.send('There was an error posting the image.');
            });
    }
});

   
    
    
// Respond to !say command
client.on('messageCreate', async (message) => {
    // Ignore messages from bots
    if (message.author.bot) return;

    // Check if the message starts with "!say"
    if (message.content.startsWith('!say')) {
        // Remove the command part "!say" and trim any whitespace
        const sayMessage = message.content.slice('!say'.length).trim();

        // If no message was provided, prompt the user to provide one
        if (!sayMessage) {
            return await message.channel.send('Please provide a message for the bot to say.');
        }

        // Send the user's message through the bot
        await message.channel.send('n');

        // Check if the bot has permission to delete the message, then delete it
        if (message.deletable) {
            await message.delete().catch((err) => {
                console.error('Failed to delete message:', err);
            });
        }
    }
});


//Moderation Commands



    // Respond to !uptime command
    if (message.content === '!uptime') {
        if (isTestMode) {
            console.warn(`${message.author.username} used !uptime`);
        }
        const totalSeconds = (client.uptime / 1000);
        const days = Math.floor(totalSeconds / 86400);
        const hours = Math.floor((totalSeconds % 86400) / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);

        const uptime = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        message.channel.send(`I have been online for: ${uptime}`);
        console.log(`Online time: ${uptime}`);
    }

    // Respond to !changelog command
    if (message.content === '!changelog') {
        const newsEmbed = new EmbedBuilder()
            .setColor(0x00ff00)
            .setTitle('Latest News')
            .setDescription(
                '**__Here are the latest updates:__**\n' +
                'an anti crash setup\nIT BETTER WORK!!!!!!!!!!!\n\n'+

                '**That\'s all for now!**'
            )
            .setFooter({ text: 'Changelog provided by AetherX Bot Devs' });

        message.channel.send({ embeds: [newsEmbed] });
        if (isTestMode) {
            console.warn(`${message.author.username} used !changelog`);
        }
    }

   
    // Respond to !yippie command and send the GIF or say "No yippe for you"
    if (message.content === '!yippie') {
        if (Math.random() < 0.01) {
            message.channel.send('No yippe for you');
        } else {
            message.channel.send('https://tenor.com/view/lethal-company-horderbug-yippee-gif-gif-5658063361159083327');
        }
        if (isTestMode) {
            console.warn(`${message.author.username} used !yippie`);
        }
    }
    
    if (message.content === 'shit') {
            message.channel.send('https://tse1.mm.bing.net/th/id/OIP.EDAz3VIJM7DB0aKqMAenOQHaNK?w=187&h=333&c=7&r=0&o=5&pid=1.7');
            if (isTestMode) {
                console.warn(`${message.author.username} needed a toilet`);
            }
    }
    

    // Respond to !about or !info command with bot information
    if (message.content === '!about' || message.content === '!info') {
        const aboutEmbed = new EmbedBuilder()
            .setColor(0x7289da)
            .setTitle('AetherX Bot Information')
            .setDescription('AetherX is a custom Discord bot designed by Androgalaxi and lmutt090.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8) or the link below.')
            .addFields(
                { name: 'Developer', value: '[Androgalaxi](https://discord.com/users/435125886996709377) and [lmutt090](https://discord.com/users/1286383453016686705)' },
                { name: 'Bot Version', value: '0.3' },
                { name: 'Bot Invite Link', value: '[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&scope=bot&permissions=8)' },
                { name: 'Support Server', value: '[Join the Support Server](https://discord.gg/yFY8Fnbtp9)' }
            )
            .setFooter({ text: 'AetherX Bot - Created with suffering by Androgalaxi and lmutt090' });

        message.channel.send({ embeds: [aboutEmbed] });
        if (isTestMode) {
            console.warn(`${message.author.username} GOT OUR INFO`);
        }
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
            const userIds = ['435125886996709377', '1286383453016686705', '1123769629165244497']; // Replace with your user IDs

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
        if (isTestMode) {
            console.warn(`${message.author.username} used !d&d roll and got a ${diceRoll}`);
        }
    }
    
    // Respond to the basic !d&d command
    if (message.content === '!d&d') {
        message.channel.send('I only have `!d&d roll`, `!d&d surrender`');
        if (isTestMode) {
            console.warn(`${message.author.username} used !d&d`);
        }
    }/*
    if (message.content === '!d&d rizz') {
        message.channel.send('@admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin @admin MUTE HIM');
                if (isTestMode) {
            console.warn(`${message.author.username} used something bad....................`);
        }
    }*/
    if (message.content === '!d&d surrender'){
        message.channel.send(':skull:')
        message.channel.send('...')
        message.channel.send('...')
        message.channel.send('...')
        message.channel.send('your ded')
        if (isTestMode) {
            console.warn(`${message.author.username} died by a falling anvil... lololololololololololololololololololololololololololololololololololololololololololololololololololololololololololol`);
        }
    }
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
    if (isTestMode) {
        console.warn(`Player has ${playerScore}`);
        console.warn(`Dealer has ${dealerScore}`);
    }

    // Check if either player or dealer starts with 21
    if (playerScore === 21 || dealerScore === 21) {
        let resultEmbed;
        if (playerScore === 21 && dealerScore === 21) {
            // Both player and dealer have 21 - it's a tie
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'tie');
            if (isTestMode) {
                console.warn('Dealer/Player win... uhhhhhhhhhhhhhhhhhhhhhhhhhhhh');
            }
        } else if (playerScore === 21) {
            // Player wins instantly
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'win');
            if (isTestMode) {
                console.warn('Player win, 21');
            }
        } else {
            // Dealer wins instantly
            resultEmbed = createResultEmbed(playerScore, dealerScore, 'lose');
            if (isTestMode) {
                console.warn('Dealer win, 21');
            }
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
            console.warn('Someone mean >:(');
        }

        if (buttonInteraction.customId === 'hit') {
            playerHand.push(getCard());
            if (isTestMode) {
                console.warn('Player hit');
                console.warn(`${playerScore}`)
            }

            if (calculateScore(playerHand) > 21) {
                // Player busts
                collector.stop('bust');
                if (isTestMode) {
                    console.warn('Player Bust');
                }
            } else {
                const updatedEmbed = createGameEmbed(playerHand, dealerHand);
                await buttonInteraction.update({ embeds: [updatedEmbed], components: [row] });
            }
        } else if (buttonInteraction.customId === 'stand') {
            if (isTestMode) {
                console.warn('Player Stand');
            }
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
                if (isTestMode) {
                    if (finalDealerScore > 21) {
                        console.warn(`Player wins, bust: ${finalPlayerScore} < ${finalDealerScore} < 21`)
                    } else {
                        console.warn(`Player win: ${finalPlayerScore} > ${finalDealerScore}`)
                    }
                }
            } else if (finalPlayerScore === finalDealerScore) {
                resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'tie');
                if (isTestMode) {
                    console.warn(`Dealer/Player win: both have ${finalPlayerScore}`);
                }
            } else {
                resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'lose');
                if (isTestMode) {
                    console.warn(`Dealer win: ${finalPlayerScore} < ${finalDealerScore}`);
                }
            }
        } else if (reason === 'forfeit') {
            resultEmbed = createResultEmbed(finalPlayerScore, finalDealerScore, 'lose');
            resultEmbed.setDescription('You forfeited the game.');
            if (isTestMode) {
                console.warn('Dealer win: Forfit');
                console.warn(`Player: ${finalPlayerScore}`)
                console.warn(`Dealer: ${finalDealerScore}`)
            }
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
        if (isTestMode) {
            console.warn(`${message.author.username} started a BlackJack game`);
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
        .setColor(0x00FF00); // Green for the prompt

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
        let embedColor = 0x00FF00; // Default to green for win
        if (userChoice === botChoice) {
            result = "It's a tie!";
            embedColor = 0xFFFF00; // Yellow for tie
        } else if (
            (userChoice === 'rock' && botChoice === 'scissors') ||
            (userChoice === 'paper' && botChoice === 'rock') ||
            (userChoice === 'scissors' && botChoice === 'paper')
        ) {
            result = 'You win!';
            embedColor = 0x00FF00; // Green for win
        } else {
            result = 'You lose!';
            embedColor = 0xFF0000; // Red for loss
        }

        // Send the result embed with the appropriate color
        const resultEmbed = new EmbedBuilder()
            .setTitle('Rock, Paper, Scissors')
            .setDescription(`You chose **${userChoice}**.\nThe bot chose **${botChoice}**.\n${result}`)
            .setColor(embedColor); // Set color based on the result

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

// Minimax algorithm for bot moves
function minimax(newBoard, depth, isMaximizing) {
    const result = checkWinner(newBoard);
    if (result === 'O') return 1; // Bot wins
    if (result === 'X') return -1; // Opponent wins
    if (newBoard.every(cell => cell !== null)) return 0; // Tie

    const availableMoves = newBoard.map((cell, index) => (cell === null ? index : null)).filter(x => x !== null);

    if (isMaximizing) {
        let bestScore = -Infinity;
        for (const move of availableMoves) {
            const tempBoard = [...newBoard];
            tempBoard[move] = 'O'; // Bot plays O
            const score = minimax(tempBoard, depth + 1, false);
            bestScore = Math.max(score, bestScore);
        }
        return bestScore;
    } else {
        let bestScore = Infinity;
        for (const move of availableMoves) {
            const tempBoard = [...newBoard];
            tempBoard[move] = 'X'; // Opponent plays X
            const score = minimax(tempBoard, depth + 1, true);
            bestScore = Math.min(score, bestScore);
        }
        return bestScore;
    }
}

// Function for bot move based on difficulty
function botMove(board, difficulty) {
    const availableMoves = board.map((cell, index) => (cell === null ? index : null)).filter(x => x !== null);

    if (difficulty === 'easy') {
        return availableMoves[Math.floor(Math.random() * availableMoves.length)]; // Random move
    }

    if (difficulty === 'medium') {
        // Medium difficulty: Try to win or block the opponent
        for (const move of availableMoves) {
            const tempBoard = [...board];
            tempBoard[move] = 'O'; // Bot plays O
            if (checkWinner(tempBoard) === 'O') return move; // Win
        }
        for (const move of availableMoves) {
            const tempBoard = [...board];
            tempBoard[move] = 'X'; // Opponent plays X
            if (checkWinner(tempBoard) === 'X') return move; // Block
        }
        return availableMoves[Math.floor(Math.random() * availableMoves.length)]; // Random move
    }

    if (difficulty === 'hard') {
        // Hard difficulty: Minimax algorithm
        let bestMove;
        let bestValue = -Infinity;

        for (const move of availableMoves) {
            const tempBoard = [...board];
            tempBoard[move] = 'O'; // Bot plays O
            const moveValue = minimax(tempBoard, 0, false);
            if (moveValue > bestValue) {
                bestValue = moveValue;
                bestMove = move;
            }
        }
        return bestMove;
    }

    return availableMoves[Math.floor(Math.random() * availableMoves.length)]; // Default move if all else fails
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
async function startTicTacToe(message, mode, difficulty = 'easy') {
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
            const botMoveIndex = botMove(board, difficulty); // Get the bot's move based on difficulty
            await updateGameBoard(botMoveIndex); // Bot makes its move
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

    const modeButtons = new ActionRowBuilder()
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

    const modeMessage = await message.channel.send({ embeds: [modeEmbed], components: [modeButtons] });

    // Create a collector to listen for mode selection
    const collector = modeMessage.createMessageComponentCollector({ time: 60000 });

    collector.on('collect', async (interaction) => {
        await interaction.deferUpdate(); // Acknowledge the button click
        const mode = interaction.customId === 'play_with_user' ? 'user' : 'bot';
        collector.stop();

        // Select difficulty after mode selection
        selectDifficulty(message, mode);
    });

    collector.on('end', async () => {
        await modeMessage.edit({ components: [] }); // Disable buttons after timeout
    });
}

// Function to select difficulty level
async function selectDifficulty(message, mode) {
    const difficultyEmbed = new EmbedBuilder()
        .setTitle('Select Difficulty Level')
        .setDescription('Choose your difficulty:\n- Easy\n- Medium\n- Hard')
        .setColor(0x00FF00);

    const difficultyButtons = new ActionRowBuilder()
        .addComponents(
            new ButtonBuilder()
                .setCustomId('easy')
                .setLabel('Easy')
                .setStyle(ButtonStyle.Primary),
            new ButtonBuilder()
                .setCustomId('medium')
                .setLabel('Medium')
                .setStyle(ButtonStyle.Secondary),
            new ButtonBuilder()
                .setCustomId('hard')
                .setLabel('Hard')
                .setStyle(ButtonStyle.Danger)
        );

    const difficultyMessage = await message.channel.send({ embeds: [difficultyEmbed], components: [difficultyButtons] });

    const filter = (interaction) => interaction.user.id === message.author.id;
    const collector = difficultyMessage.createMessageComponentCollector({ filter, time: 60000 });

    collector.on('collect', async (interaction) => {
        await interaction.deferUpdate(); // Acknowledge the button click
        const difficulty = interaction.customId; // Get selected difficulty
        collector.stop();

        // Create an embed to confirm the selected difficulty
        const confirmationEmbed = new EmbedBuilder()
            .setTitle('Difficulty Selected')
            .setDescription(`${interaction.user}, you have selected **${difficulty}** difficulty.`)
            .setColor(0x00FF00);

        await message.channel.send({ embeds: [confirmationEmbed] }); // Send confirmation message

        // Start the Tic-Tac-Toe game with selected difficulty
        await startTicTacToe(message, mode, difficulty);
    });

    collector.on('end', async () => {
        await difficultyMessage.edit({ components: [] }); // Disable buttons after timeout
    });
}

// Export the command for Tic-Tac-Toe
module.exports = {
    name: 'ttt',
    description: 'Play Tic-Tac-Toe!',
    execute(message) {
        selectTicTacToeMode(message);
    },
};

// Call the function to start the game (example)
client.on('messageCreate', async (message) => {
    if (message.content === '!tictactoe' || message.content === '!ttt') {
        await selectTicTacToeMode(message); // Initiate game mode selection
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

// Listen for "!stroke" to cause a stroke
client.on('messageCreate', async (message) => {
    if (message.content === '!stroke' || message.content === '!S T R O K E' || message.content === 'Ey boss') {
        // Read the content of the .txt file
        console.log(`${message.author.username} wanted me to have a stroke...`)
        const filePath = path.join(__dirname, 'msg', 'HEEEELP!.txt');
        
        fs.readFile(filePath, 'utf8', async (err, data) => {
            if (err) {
                console.error('Error reading the file:', err);
                return message.channel.send('There was an error reading the help file.');
            }

            // Send the content of the .txt file as the initial message
            const sentMessage = await message.channel.send(data);

            // Wait for 10 seconds (10000 ms)
            setTimeout(async () => {
                // Edit the original message to :skull:
                await sentMessage.edit(`:skull:`);
            }, 1000); // 10-second delay
        });
    }
});

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
        const userAnswerText = trivia.options[userAnswer.charCodeAt(0) - 65]; // Get the corresponding answer option
        let responseEmbed;

        if (userAnswerText === trivia.answer) {
            responseEmbed = new EmbedBuilder()
                .setTitle('Correct Answer!')
                .setDescription(`You got it right! The correct answer was: **${trivia.answer}**.`)
                .setColor(0x00FF00); // Green for correct
        } else {
            responseEmbed = new EmbedBuilder()
                .setTitle('Wrong Answer!')
                .setDescription(`You chose: **${userAnswerText}**\nThe correct answer was: **${trivia.answer}**.`)
                .setColor(0xFF0000); // Red for incorrect
        }

        // Update the original trivia message with the response and keep the options displayed
        await triviaMessage.edit({ embeds: [triviaEmbed, responseEmbed], components: [] });

        // Stop the collector after an answer is submitted
        collector.stop();
    });

    collector.on('end', async (collected, reason) => {
        if (reason === 'time') {
            // Only show the timeout message if no answers were collected
            if (collected.size === 0) {
                const timeoutEmbed = new EmbedBuilder()
                    .setTitle('Time is Up!')
                    .setDescription('No answer was selected within the time limit.')
                    .setColor(0xFFFF00); // Yellow for timeout

                await triviaMessage.edit({ embeds: [timeoutEmbed], components: [] });
            }
            // If collected.size > 0, an answer was submitted and no additional message is needed
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
        const selectedEmbed = new EmbedBuilder()
            .setTitle('Category Selected')
            .setDescription(`You have selected: **${categories.find(cat => cat.categoryId.toString() === selectedCategory).label}**`)
            .setColor(0x00FF00);

        await interaction.update({ embeds: [selectedEmbed], components: [] });
        await startTriviaGame(message, selectedCategory); // Start the trivia game with the selected category
    });

    collector.on('end', async (collected, reason) => {
        if (reason === 'time') {
            const timeoutEmbed = new EmbedBuilder()
                .setTitle('Game Cancelled')
                .setDescription('No category selected. Please try again later.')
                .setColor(0xFF0000); // Red for cancellation

            await categoryMessage.edit({ embeds: [timeoutEmbed], components: [] });
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

client.on(Events.MessageCreate, (message) => {
    if (message.content.startsWith('!news')) {
        if (allowedUsers.includes(message.author.id)) {
            const userMessage = message.content.slice('!news'.length).trim();

            if (!userMessage) {
                message.channel.send('Please provide a message to send.');
                console.log(`News posting failed: No message content provided by ${message.author.tag} (${message.author.id})`);
                return;
            }

            // Get the color based on the author's ID, or default to a neutral color if not specified
            const embedColor = userColorsN[message.author.id] || '#1e90ff';

            // Create the embed with the dynamic color
            const embed = new EmbedBuilder()
                .setTitle('AetherX News Update')
                .setDescription(`${userMessage}\n\n*Use !changelog for updates we didn't list in this news notice.*`)
                .addFields({ name: 'Posted By', value: `<@${message.author.id}>` })
                .setColor(embedColor) // Dynamic color based on user
                .setTimestamp()
                .setFooter({
                    text: 'AetherX News!',
                    iconURL: 'https://cdn.discordapp.com/avatars/1067646246254284840/f251941fb561142385414ab7e4bb0d50?size=1024',
                });

            if (designatedChannel) {
                designatedChannel.send({
                    content: 'News Kiddos!!!!',
                    embeds: [embed],
                })
                .then(() => {
                    console.log(`News posted by ${message.author.tag} (${message.author.id}): ${userMessage}`);
                })
                .catch((error) => {
                    console.log(`Failed to post news by ${message.author.tag} (${message.author.id}). Error: ${error}`);
                });
            } else {
                message.channel.send('Designated channel not found.');
                console.log(`News posting failed: Designated channel not found for ${message.author.tag} (${message.author.id})`);
            }
        } else {
            message.channel.send('You do not have permission to use this command. :middle_finger:');
            console.log(`Unauthorized news posting attempt by ${message.author.tag} (${message.author.id})`);
        }
    }
});

//Start of Tickets

// Respond to !nh command
client.on('messageCreate', async (message) => {
    if (message.content === '!nh') {
        const nhEmbed = new EmbedBuilder()
            .setTitle('Support Information')
            .setDescription('For assistance, DM the bot with `!ticket` to create a support ticket.')
            .setColor('DarkBlue')
            .setFooter({ text: 'Our team will assist you shortly.' });

        const channel = message.guild.channels.cache.get('1115793036023181342'); // Replace with the channel ID where the message should go
        if (channel) channel.send({ embeds: [nhEmbed] });
    }
});

// Create Ticket via DM
client.on('messageCreate', async (message) => {
    // Ticket creation command
    if (message.guild === null && message.content === '!ticket') {
        const guild = client.guilds.cache.get('1067095151736012902'); // Replace with your server ID
        if (!guild) return;

        const category = guild.channels.cache.get('1304564673621917696'); // Replace with your category ID
        if (!category) return;

        const ticketChannel = await guild.channels.create(`ticket-${message.author.id}`, {
            type: 'GUILD_TEXT',
            parent: category.id,
            permissionOverwrites: [
                { id: message.author.id, allow: ['VIEW_CHANNEL', 'SEND_MESSAGES'] },
                { id: guild.roles.everyone.id, deny: ['VIEW_CHANNEL'] },
                { id: 'STAFF_ROLE_ID', allow: ['VIEW_CHANNEL', 'SEND_MESSAGES'] } // Replace with your staff role ID
            ]
        });

        const ticketEmbed = new MessageEmbed()
            .setTitle('Ticket Created')
            .setDescription('A support team member will assist you shortly.')
            .setColor('DarkBlue');

        await message.author.send({ embeds: [ticketEmbed] }).catch(() => 
            message.reply('Unable to send a DM.')
        );
        ticketChannel.send(`<@${message.author.id}> Ticket created! A staff member will be with you shortly.`);
    }

    // Staff handling messages in ticket channels
    else if (message.channel.parentId === 'YOUR_CATEGORY_ID') { // Replace with your category ID
        const userID = message.channel.name.split('-')[1];
        const user = await client.users.fetch(userID).catch(() => null);

        if (user) {
            // Pre-made messages and ticket management commands
            if (message.content.startsWith('ax!hello')) {
                const helloEmbed = new MessageEmbed()
                    .setDescription('Hello! How can we assist you today?')
                    .setColor('DarkBlue');
                await user.send({ embeds: [helloEmbed] });
            } else if (message.content.startsWith('ax!notify')) {
                // Add custom logic for notify if needed
            } else if (message.content.startsWith('ax!pm1')) {
                const pm1Embed = new MessageEmbed()
                    .setDescription('We would love to partner with you! Here’s our ad for you to post.')
                    .setColor('DarkBlue');
                await user.send({ embeds: [pm1Embed] });
            } else if (message.content.startsWith('ax!pm2')) {
                const pm2Embed = new MessageEmbed()
                    .setDescription('Thank you for posting our ad! We have confirmed the partnership.')
                    .setColor('DarkBlue');
                await user.send({ embeds: [pm2Embed] });
            } else if (message.content.startsWith('ax!morehelp')) {
                const moreHelpEmbed = new MessageEmbed()
                    .setDescription('Is there anything else we can assist you with?')
                    .setColor('DarkBlue');
                await user.send({ embeds: [moreHelpEmbed] });
            } else if (message.content.startsWith('ax!needreply')) {
                const needReplyEmbed = new MessageEmbed()
                    .setDescription('We need a response from you. If we don’t hear back within 12 hours, we will close the ticket automatically.')
                    .setColor('DarkBlue');
                await user.send({ embeds: [needReplyEmbed] });

                // Close ticket after 12 hours if no response
                setTimeout(async () => {
                    const updatedChannel = message.guild.channels.cache.get(message.channel.id);
                    if (updatedChannel) {
                        await updatedChannel.delete();
                        await user.send('Your ticket has been closed due to no response. If you need further assistance, feel free to open a new ticket.');
                    }
                }, 12 * 60 * 60 * 1000); // 12 hours in milliseconds
            } else if (message.content.startsWith('ax!close')) {
                await message.channel.delete();
                await user.send('Your ticket has been closed. If you need further assistance, feel free to open a new ticket.');
            }

            // Staff sending images to users
            else if (message.attachments.size > 0) {
                const attachment = message.attachments.first();
                const imageEmbed = new MessageEmbed()
                    .setDescription('Here’s an image from our support team:')
                    .setImage(attachment.url)
                    .setColor('DarkBlue');
                await user.send({ embeds: [imageEmbed] });
            }

            // Staff general response to user via `ax!` prefix command
            else if (message.content.startsWith('ax!')) {
                const args = message.content.split(' ').slice(1).join(' ');
                const generalResponseEmbed = new MessageEmbed()
                    .setDescription(args)
                    .setColor('DarkBlue');
                await user.send({ embeds: [generalResponseEmbed] });
                await message.channel.send('Message sent to the user.');
            }
        } else {
            await message.channel.send('User not found.');
        }
    }
});

//End of Tickets

client.on("message", async (message) => {
    // Command to restart the bot
    if (message.content === "!restart") {
        // Check if the user is in the allowed list
        if (allowedUsers.includes(message.author.id)) {
            await message.channel.send("Restarting bot...");
            console.log($(message.author.id) + "has restarted the bot")
            
            // Restart logic - kill process to allow automatic restart or programmatic restart
            process.exit(); // This exits the current process to trigger a restart
        } else {
            message.channel.send("You do not have permission to restart the uptime counter.");
        }
    }
});

// Function to fetch data from StartGG
async function queryStartGG(query, variables) {
  try {
    const response = await startGGAPI.post('', { query, variables });
    return response.data.data;
  } catch (error) {
    console.error('Error:', error);
    return null;
  }
}

// Command listener
client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  if (message.content.startsWith('!tournament')) {
    const tournamentQuery = `
      query($name: String!) {
        tournaments(query: {name: $name}) {
          nodes {
            id
            name
          }
        }
      }
    `;
    const name = message.content.split(' ')[1] || 'smash';
    const result = await queryStartGG(tournamentQuery, { name });
    if (result && result.tournaments.nodes.length > 0) {
      result.tournaments.nodes.forEach(tournament => {
        message.channel.send(`**Tournament:** ${tournament.name} (ID: ${tournament.id})`);
      });
    } else {
      message.channel.send('No tournaments found.');
    }
  }

  if (message.content.startsWith('!hub')) {
    const hubQuery = `
      query($slug: String!) {
        hub(slug: $slug) {
          id
          name
        }
      }
    `;
    const slug = message.content.split(' ')[1] || 'smash';
    const result = await queryStartGG(hubQuery, { slug });
    if (result && result.hub) {
      message.channel.send(`**Hub:** ${result.hub.name} (ID: ${result.hub.id})`);
    } else {
      message.channel.send('Hub not found.');
    }
  }

  if (message.content.startsWith('!team')) {
    const teamQuery = `
      query($slug: String!) {
        team(slug: $slug) {
          id
          name
        }
      }
    `;
    const slug = message.content.split(' ')[1] || 'team-name';
    const result = await queryStartGG(teamQuery, { slug });
    if (result && result.team) {
      message.channel.send(`**Team:** ${result.team.name} (ID: ${result.team.id})`);
    } else {
      message.channel.send('Team not found.');
    }
  }

  if (message.content.startsWith('!user')) {
    const userQuery = `
      query($userId: String!) {
        user(id: $userId) {
          id
          username
        }
      }
    `;
    const userId = message.content.split(' ')[1] || 'user-id';
    const result = await queryStartGG(userQuery, { userId });
    if (result && result.user) {
      message.channel.send(`**User:** ${result.user.username} (ID: ${result.user.id})`);
    } else {
      message.channel.send('User not found.');
    }
  }
});


client.login(process.env.BOT_TOKEN);
