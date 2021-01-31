import discord
from discord.ext import commands
import os
from settings import DISCORD_API_KEY
from settings import ROOT_PHOTO_FOLDER_ID
import io
import random
import asyncio

# Features
import example_feat
import google_drive_feat

# Use bot commands extension.
# Tutorial: https://discordpy.readthedocs.io/en/latest/ext/commands/index.html
# API: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#bot

# File Documentation: https://discordpy.readthedocs.io/en/latest/api.html#file
# Embed Documentation: https://discordpy.readthedocs.io/en/latest/api.html#discord.Embed
# Context Documentation: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.Context

# ================================================================================
# Global vars

photo_requests = {}
bot_channels = {}

# ================================================================================
# Temp directory
temp_dir = "./bool_bot/files/"

# Bot is subclass of client. Any coroutines that defines an event should be usable under bot.
bot = commands.Bot(command_prefix='!')

# ================================================================================
# Bot Configuration
bot.description = ""

# ================================================================================
# Events.

@bot.event
async def on_ready():
    """
    Coroutine event. Invoked when bot starts up
    """
    print('Logged on as {0}!'.format(bot.user.name))

@bot.event
async def on_message(message):
    """
    Coroutine event. Invoked when user sends a message
    """

    if (message.content.find("!channel") != -1):
        return await bot.process_commands(message)

    if message.channel.name in bot_channels:

        result = await bot.process_commands(message)

        # Ensure no feedback loop.
        if message.author.name != bot.user.name and message.content[0] != "!":
            #Uncomment next line to test on_message
            await process_search_request(message)
            # await example_feat.send_mess(message)

@bot.event
async def on_command_error(context, exception):
    """
    Coroutine event. Invoked when error has occurred with processing a command.
    """
    await context.send("An error has occurred with your request. {0}".format(exception))


# ================================================================================
# Commands

@bot.command(name="files")
async def files(ctx):
    """
    Command for returning the recent files on google drive.
    """
    files = google_drive_feat.get_recent_files()

    # print(files)

    output = "\n"
    for file in files:
        print(file)
        output += (file["name"] + "\n")

    await ctx.send(output)

@bot.command(name="phototest")
async def phototest(ctx):
    """
    Testing if local photo can be uploaded to discord. Type !phototest
    """
    file_buffered_io_stream = open("./bool_bot/files/red.jpeg", "rb")
    file_photo = discord.File(file_buffered_io_stream, filename="red.jpeg")

    embed = discord.Embed(title="The Gang", description="Wow an uploaded image")
    embed.set_image(url="attachment://red.jpeg")

    await ctx.send("Sending Photo", file=file_photo, embed=embed)

@bot.command(name="photo")
async def photo(ctx, search_option, query):
    """
    Photo commands. Refer below for commands.

    Flags

    s or search - Search for a photo via name. Ex. !photo s kurt
    e or exact - Return a photo with exact name. Ex. !photo e davidmald.jpg
    i or id - Return a photo by google drive id. Ex. !photo i 1CeUaHMY5-Fm5XD36u3QWUZLaG6qAZUPq
    r or random - Return a photo randomly from a query. Ex. !photo r justin
    rf or randomfile - Return a photo randomly from a specified folder. Ex. !photo rf test

    """

    if search_option == "s" or search_option == "search":
        # Searches for photos with name
        await photo_search(ctx, query)
    elif search_option == "e" or search_option == "exact":
        # Find and return photo with exact name
        await photo_name(ctx, query)
    elif search_option == "i" or search_option == "id":
        # Find and return photo with google id
        await photo_id(ctx, query)
    elif search_option == "r" or search_option == "random":
        # Return random photo from recent files list
        await photo_random(ctx, query)
    elif search_option == "rf" or search_option == "randomfile":
        # Return random photo from a specified folder
        await folder_random(ctx, query)
    else:
        await ctx.send("Something is wrong with your query, most likely that the option you provided is not valid")

@bot.command(name="listrequests")
async def list_requests(ctx):
    """
    A development command to inspect the photo requests
    """
    print(photo_requests)

@bot.command(name="ls")
async def ls(ctx):
    """
    Lists the subdirectories in root photo folder. Useful for finding a random photo in a folder
    """
    folder_ids, folder_names = google_drive_feat.get_folder_ids(ROOT_PHOTO_FOLDER_ID)
    description = ''

    for i in range(len(folder_names)-1):
        description += "{0}. {1}\n".format(i, folder_names[i])
        # Send decision embed
    embed = discord.Embed(title='Sub-directories found:')
    embed.description = description

    # Takes discord message type
    message = await ctx.send(embed=embed)
    
@bot.command(name="channel-list")
async def channel_list(ctx):
    """
    Command to list which channels is the bot allowed be issued commands
    """
    channels = ctx.guild.text_channels
    
    bot_active_channels = []
    bot_nonactive_channels = []

    for channel in channels:
        if channel.name in bot_channels:
            bot_active_channels.append(channel.name)
        else:
            bot_nonactive_channels.append(channel.name)        

    active_bot_message = "\n".join(bot_active_channels)
    nonactive_bot_message = "\n".join(bot_nonactive_channels)

    message = "Bot Access Channels\n\n{0}\n\nBot Non Access Channels\n\n{1}".format(active_bot_message, nonactive_bot_message)
    embed = discord.Embed(title="Bot Permissions channel", description=message)
    return await ctx.send("", embed=embed)

@bot.command(name="channel")
async def channel(ctx, flag, query):
    """
    Add or remove bot from a specific channel. If added to a specific channel, regular users can issue bot commands. 
    WARNING: Need to be an admin of the guild to issue this command

    Flags
    a or add - Add a bot to a channel. Ex. !channel a bool-bol-test
    d or delete - Remove a bot from a channel. Ex. !channel d bool-bot-test
    """

    # Make sure user is an admin

    if not ctx.author.guild_permissions.administrator:
        return

    if flag == "a" or flag == "add":
        await channel_add(ctx, query)
    elif flag == "r" or flag == "remove":
        await channel_remove(ctx, query)
    else:
        return await ctx.send("Issues with your request. Are you sure you are entering the right flags")

# ================================================================================
# Photo functions

async def folder_random(ctx, query):
    """
    Send a photo randomly by querying a folder. Type !photo rf test
    """

    files = google_drive_feat.get_folder_contents(query)


    if files == "No Folder":
        return await ctx.send("Folder {0} cannot be found".format(query))
    elif files == "Multiple Folders":
        return await ctx.send("Multiple folders with name {0}. Stopping request".format(query))
    elif len(files) == 0:
        return await ctx.send("No files in folder {0}". format(query))

    random_index = random.randint(0, len(files) - 1)
    random_file_id = files[random_index]["id"]

    await send_photo(ctx, random_file_id, "{0}.jpeg".format(random_file_id), "Random photo from {0}".format(query))


async def photo_random(ctx, query):
    """
    Send random photo based on name in query.

    Ex. !photo r justin
    This command will return a random photo, where the file name begins with "justin"

    """
    found_files = google_drive_feat.get_files_search(query)

    if len(found_files) == 0:
        await ctx.send("No random photo found, probably because there are no photo/file names with the query you requested")
        return

    random_index = random.randint(0, len(found_files) - 1)
    random_file_id = found_files[random_index]["id"]

    await send_photo(ctx, random_file_id, "{0}.jpeg".format(random_file_id), "A random picture")



async def photo_id(ctx, file_id):
    """
    Send a photo by photo id. Type !photo_id "google_file_id"

    Ex. !photo 1vACqpQLkve6mLC1tIAEmlrZoUiiaoiaU
    """
    await send_photo(ctx, file_id, "{0}.jpeg".format(file_id), "Wow downloaded from google drive")

async def photo_name(ctx, photo_name):
    """
    Send a photo by exact photo name including extension. Type !photo "photo name"

    Ex. !photo jeyalex111.jpg
    """
    obj = google_drive_feat.get_file_id(photo_name)

    if len(obj) == 0:
        await ctx.send("No photo found by that name")
        return

    file_id = obj[0]['id']
    file_name = obj[0]['name']
    web_link = obj[0]["webViewLink"]

    await send_photo(ctx, file_id, file_id, web_link)

async def photo_search(ctx, query):
    """
    Helper function for command photo s query. Process request of a query. Returns an embed with options.
    """

    #Check if current user has a pending request
    if (ctx.author.id in photo_requests):
        # Found pending request. Deny
        return await ctx.send("Pending request, please chose or enter c to cancel")

    # Continue with query
    found_files = google_drive_feat.get_files_search(query)

    if len(found_files) == 0:
        await ctx.send("There are no photos that start with {}".format(query)) # await neeeded???
        return

    description = ""

    for i in range(0 , len(found_files)):
        file = found_files[i]

        description += "{0}. {1}\n".format(i, file['name'])

    # Send decision embed
    embed = discord.Embed(title="Select an option. Enter a number from list. Enter c to cancel")
    embed.description = description

    # Takes discord message type
    message = await ctx.send(embed=embed)

    # Store found_files and message in a dictionary.
    request = {
        "files": found_files,
        "message": message
    }


    # Push request to photo requests
    photo_requests[ctx.author.id] = request
    try:
        await bot.wait_for('message',timeout=10.0)
    except asyncio.TimeoutError:
        del photo_requests[ctx.author.id]
        await message.delete()
        await ctx.send('Request {} timed out'.format(query))

async def send_photo(ctx, file_id, file_name, description):
    """
    Sends the photo to where the command is issued

    ctx : Context - A contex class. Part of discord.py. Refer to do here (https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#context)
    file_id : String - The google drive file id.
    file_name : String - The output file name shown in discord.
    description : String - The description of the photo in discord embed
    """

    photo_name = google_drive_feat.download_photo(file_id, file_name)

    # Reads file from local storage
    buffered = open(temp_dir + photo_name, "rb")
    file_photo = discord.File(buffered, filename=photo_name)

    embed = discord.Embed(title=photo_name, description=description)
    embed.set_image(url="attachment://" + photo_name)

    await ctx.send("Sending Photo", file=file_photo, embed=embed)

    buffered.close()

    # Deletes file from local storage
    os.remove(temp_dir + photo_name)


    return

async def process_search_request(message):
    """
    Process search request of requesting user
    """
    user_id = message.author.id
    res = message.content


    if not (user_id in photo_requests):
        # Found nothing. No request for this user.
        return

    if bool(photo_requests) and photo_requests[user_id] != None and message.content == 'c':

        message = photo_requests[user_id]["message"]
        # Delete query embed
        await message.delete()

        del photo_requests[user_id]

        return await message.channel.send("Cancelling Request")

    if bool(photo_requests) and photo_requests[user_id] != None:

        index = None
        try:
            index = int(res)
        except ValueError:
            return await message.channel.send("Please enter a number")

        try:
            file_id = photo_requests[user_id]["files"][index]["id"]
            file_name = photo_requests[user_id]["files"][index]["name"]
            description = photo_requests[user_id]["files"][index]["webViewLink"]

            message = photo_requests[user_id]["message"]

            # Delete query embed
            await message.delete()

            # Third argument takes file id as the file name. Due to privacy reasons, we won't upload the photo name to discord
            await send_photo(message.channel, file_id, "{0}.jpeg".format(file_id), description)
        except IndexError:
            return await message.channel.send("Please enter a number in range of request")

        # Remove user key from photo requests
        del photo_requests[user_id]

        return

# ================================================================================
# Channel functions

async def channel_add(ctx, name):
    """
    Add a bot to a channel via name
    """

    if name in bot_channels:
        return await ctx.send("Channel already added")

    channels = ctx.guild.text_channels

    found_channels = filter(lambda channel: channel.name == name, channels)

    if len(list(found_channels)) > 0:
        bot_channels[name] = "no"
        return await ctx.send("Sucessfully added to {0} text channel".format(name))

    return await ctx.send("Cannot find channel {0}".format(name))

async def channel_remove(ctx, name):
    """
    Delete a bot from a channel via name
    """
    
    channels = ctx.guild.text_channels
    found_channels = filter(lambda channel: channel.name == name, channels)

    if not (name in bot_channels) and len(list(found_channels)) > 0:
        return await ctx.send("Cannot delete channel. Channel is not in this channel already")

    if len(list(found_channels)) > 0:
        del bot_channels[name]
        return await ctx.send("Sucessfully remove bot from {0} text channel".format(name))

    return await ctx.send("Cannot find channel {0}".format(name))

def main():
    """
    The entry point for the bot. Called in __main__.py
    """
    bot.run(DISCORD_API_KEY)
